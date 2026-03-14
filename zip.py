#!/usr/bin/env python3
import os
import shutil
import zipfile

source_dir = "/Users/simxn/Documents/Geschäft/project7III/Apps/7III Tap/MIDI Remote Script/Tap"
target_dir = "/Users/simxn/Documents/Geschäft/project7III/Apps/7III Tap/MIDI Remote Script/ZIP/Tap"
zip_path = "/Users/simxn/Documents/Geschäft/project7III/Apps/7III Tap/MIDI Remote Script/ZIP/Tap.zip"

files_to_copy = ["__init__.py", "Tap.py", "README.md"]

print(f"Creating target directory: {target_dir}")
os.makedirs(target_dir, exist_ok=True)

print(f"Clearing {target_dir}...")
for item in os.listdir(target_dir):
    item_path = os.path.join(target_dir, item)
    if os.path.isfile(item_path):
        os.remove(item_path)
        print(f"  Removed: {item}")

print(f"\nCopying files to {target_dir}...")
for filename in files_to_copy:
    source_path = os.path.join(source_dir, filename)
    if os.path.exists(source_path):
        shutil.copy2(source_path, target_dir)
        print(f"  Copied: {filename}")
    else:
        print(f"  Warning: {filename} not found")

print(f"\nCreating zip: {zip_path}")
if os.path.exists(zip_path):
    os.remove(zip_path)

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, os.path.dirname(target_dir))
            zipf.write(file_path, arcname)
            print(f"  Added to zip: {arcname}")

print("\nDone!")
