import ast
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME_FILES = (
    "tap_runtime.py",
    "device_banks.py",
    "tap_protocol.py",
    "automation.py",
    "Tap.py",
    "__init__.py",
)


def _literal_assignment(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name
               for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("Missing literal assignment: {}".format(name))


class RemoteScriptPackagingTests(unittest.TestCase):
    def test_deploy_manifest_lists_helpers_before_entrypoint(self):
        manifest = _literal_assignment(ROOT / "deploy.py", "runtime_files")
        self.assertEqual(tuple(manifest), RUNTIME_FILES)

    def test_zip_manifest_lists_helpers_and_uses_relative_root(self):
        zip_source = (ROOT / "zip.py").read_text(encoding="utf-8")
        manifest = _literal_assignment(ROOT / "zip.py", "runtime_files")
        self.assertEqual(tuple(manifest), RUNTIME_FILES)
        self.assertNotIn("Gescha", zip_source)
        self.assertNotIn("Geschäft", zip_source)
        self.assertIn("Path(__file__).resolve().parent", zip_source)

    def test_tap_imports_extracted_helpers_as_package_modules(self):
        tree = ast.parse((ROOT / "Tap.py").read_text(encoding="utf-8"))
        imports = {
            (node.module, node.level): {
                alias.name for alias in node.names
            }
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
        }
        self.assertIn(("device_banks", 1), imports)
        self.assertIn("TapDeviceComponent", imports[("device_banks", 1)])
        self.assertIn(("tap_runtime", 1), imports)
        self.assertTrue({
            "TapScheduledCall",
            "TapPerformanceDiagnostics",
        }.issubset(imports[("tap_runtime", 1)]))
        self.assertIn(("tap_protocol", 1), imports)
        self.assertTrue({
            "TAP_SYSEX_APP_TO_REMOTE",
            "TAP_SYSEX_APP_TO_REMOTE_SPECS",
            "TAP_SYSEX_REMOTE_TO_APP",
            "TAP_SYSEX_REMOTE_TO_APP_SPECS",
        }.issubset(imports[("tap_protocol", 1)]))
        self.assertIn(("automation", 1), imports)
        self.assertTrue({
            "AutomationEvent",
            "AutomationTransferCoordinator",
            "ExactAutomationWriteTransaction",
            "LiveAutomationWriter",
        }.issubset(imports[("automation", 1)]))
        self.assertNotIn(
            "TapDeviceComponent",
            {node.name for node in tree.body if isinstance(node, ast.ClassDef)},
        )
        self.assertNotIn(
            "TapScheduledCall",
            {node.name for node in tree.body if isinstance(node, ast.ClassDef)},
        )
        protocol_tree = ast.parse(
            (ROOT / "tap_protocol.py").read_text(encoding="utf-8")
        )
        protocol_names = {
            node.name for node in protocol_tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        }
        protocol_names.update(
            target.id
            for node in protocol_tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        )
        self.assertTrue({
            "TapSysExMessageSpec",
            "_tap_sysex_spec",
            "_tap_sysex_registry",
        }.issubset(protocol_names))
        automation_tree = ast.parse(
            (ROOT / "automation.py").read_text(encoding="utf-8")
        )
        automation_names = {
            node.name for node in automation_tree.body
            if isinstance(node, ast.ClassDef)
        }
        self.assertTrue({
            "AutomationEvent",
            "AutomationTransferCoordinator",
            "ExactAutomationWriteTransaction",
            "LiveAutomationWriter",
        }.issubset(automation_names))

    def test_optional_device_bank_imports_only_handle_missing_modules(self):
        tree = ast.parse(
            (ROOT / "device_banks.py").read_text(encoding="utf-8")
        )
        import_try_blocks = [
            node for node in tree.body
            if isinstance(node, ast.Try) and any(
                isinstance(statement, ast.ImportFrom)
                for statement in node.body
            )
        ]
        self.assertGreaterEqual(len(import_try_blocks), 6)
        for node in import_try_blocks:
            self.assertEqual(
                [
                    handler.type.id
                    for handler in node.handlers
                    if isinstance(handler.type, ast.Name)
                ],
                ["ImportError"],
            )

    def test_staged_package_and_zip_contain_all_runtime_files(self):
        # Run the real ZIP builder against a temporary checkout so this test
        # does not depend on the untracked distribution directory being present.
        with tempfile.TemporaryDirectory() as temporary_dir:
            staged_source = pathlib.Path(temporary_dir) / "Tap"
            staged_source.mkdir()
            for filename in RUNTIME_FILES + ("README.md", "zip.py"):
                shutil.copy2(ROOT / filename, staged_source / filename)
            subprocess.run(
                [sys.executable, str(staged_source / "zip.py")],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            staged_dir = pathlib.Path(temporary_dir) / "ZIP" / "Tap"
            archive_path = pathlib.Path(temporary_dir) / "ZIP" / "Tap.zip"
            self.assertTrue(staged_dir.is_dir(), staged_dir)
            self.assertTrue(archive_path.is_file(), archive_path)
            for filename in RUNTIME_FILES:
                self.assertTrue((staged_dir / filename).is_file(), filename)

            with zipfile.ZipFile(str(archive_path)) as archive:
                names = archive.namelist()
        expected_names = ["Tap/{}".format(filename) for filename in RUNTIME_FILES]
        for name in expected_names:
            self.assertIn(name, names)
        positions = [names.index(name) for name in expected_names]
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
