#!/usr/bin/env python3
# Deploy script for Tap MIDI Remote Script
# Clears the Ableton User Library Remote Scripts/Tap folder and copies the latest files

import os
import shutil

source_dir = "/Users/simxn/Documents/Geschäft/project7III/Apps/7III Tap/MIDI Remote Script/Tap"
target_dir = "/Users/simxn/Music/Ableton/User Library/Remote Scripts/Tap"

files_to_copy = ["__init__.py", "Tap.py"]

# Clear all files in the target directory
print(f"Clearing {target_dir}...")
for item in os.listdir(target_dir):
    item_path = os.path.join(target_dir, item)
    if os.path.isfile(item_path):
        os.remove(item_path)
        print(f"  Removed: {item}")

# Copy source files to the target directory
print(f"\nCopying files to {target_dir}...")
for filename in files_to_copy:
    source_path = os.path.join(source_dir, filename)
    if os.path.exists(source_path):
        shutil.copy2(source_path, target_dir)
        print(f"  Copied: {filename}")
    else:
        print(f"  Warning: {filename} not found")

print("\nDone!")
