#!/usr/bin/env python3
# Build script for Tap MIDI Remote Script distribution
# Copies files to ZIP/Tap folder and creates a Tap.zip file for distribution

import shutil
import zipfile
from pathlib import Path

source_dir = Path(__file__).resolve().parent
distribution_dir = source_dir.parent / "ZIP"
target_dir = distribution_dir / "Tap"
zip_path = distribution_dir / "Tap.zip"

# Keep helper modules ahead of the package entry point in both the staging
# folder and the ZIP manifest.  The paths are relative to this script so the
# build works from any checkout location and Unicode normalization is irrelevant.
runtime_files = (
    "tap_runtime.py",
    "device_banks.py",
    "tap_protocol.py",
    "automation.py",
    "Tap.py",
    "__init__.py",
)
documentation_files = ("README.md",)
files_to_copy = runtime_files + documentation_files

# Create target directory if it doesn't exist
print(f"Creating target directory: {target_dir}")
target_dir.mkdir(parents=True, exist_ok=True)

# Clear all files in the target directory
print(f"Clearing {target_dir}...")
for item_path in target_dir.iterdir():
    if item_path.is_file():
        item_path.unlink()
        print(f"  Removed: {item_path.name}")

# Copy source files to the target directory
print(f"\nCopying files to {target_dir}...")
for filename in files_to_copy:
    source_path = source_dir / filename
    if source_path.is_file():
        shutil.copy2(source_path, target_dir / filename)
        print(f"  Copied: {filename}")
    else:
        print(f"  Warning: {filename} not found")

# Create zip file
print(f"\nCreating zip: {zip_path}")
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
    for filename in files_to_copy:
        file_path = target_dir / filename
        if file_path.is_file():
            arcname = file_path.relative_to(target_dir.parent)
            zipf.write(str(file_path), str(arcname))
            print(f"  Added to zip: {arcname}")

print("\nDone!")
