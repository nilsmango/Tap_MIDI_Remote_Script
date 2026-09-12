#!/usr/bin/env python3
# Deploy script for Tap MIDI Remote Script
# Atomically copies Tap into the Ableton User Library and clears stale bytecode.

import filecmp
import os
import shutil
from pathlib import Path

source_dir = Path(__file__).resolve().parent
target_dir = Path.home() / "Music" / "Ableton" / "User Library" / "Remote Scripts" / "Tap"

# Keep helper modules ahead of the package entry point so a deployment never
# briefly exposes an __init__.py whose imports cannot yet be resolved.
runtime_files = (
    "tap_runtime.py",
    "device_banks.py",
    "tap_protocol.py",
    "automation.py",
    "Tap.py",
    "__init__.py",
)

target_dir.mkdir(parents=True, exist_ok=True)

# Live's embedded Python can otherwise retain bytecode from an earlier deploy.
bytecode_dir = target_dir / "__pycache__"
if bytecode_dir.exists():
    print(f"Clearing stale bytecode: {bytecode_dir}")
    shutil.rmtree(bytecode_dir)

# Copy each file atomically so Live never sees a partially written script.
print(f"Copying files from {source_dir} to {target_dir}...")
for filename in runtime_files:
    source_path = source_dir / filename
    target_path = target_dir / filename
    staged_path = target_dir / (filename + ".deploying")
    if not source_path.is_file():
        raise FileNotFoundError(f"Required source file not found: {source_path}")
    try:
        shutil.copy2(source_path, staged_path)
        os.replace(staged_path, target_path)
    finally:
        if staged_path.exists():
            staged_path.unlink()
    if not filecmp.cmp(source_path, target_path, shallow=False):
        raise RuntimeError(f"Deployment verification failed for {filename}")
    print(f"  Copied and verified: {filename}")

print("Done. Fully quit and reopen Live so it rescans Remote Scripts.")
