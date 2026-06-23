import json
import sys

sys.path.insert(0, '..')

from modules.fs_metadata import scan_directory

path = r"C:\Users"

# ── Test 1: Non-recursive ──────────────────────────────────────────────
# Scans only the immediate contents of the folder, no subfolders
print("=== Non-Recursive Scan ===")
result_shallow = scan_directory(path, recursive=False)

print(f"Scanned directory : {result_shallow['scanned_directory']}")
print(f"Total files found : {result_shallow['total_files_found']}")
print(f"Total errors      : {result_shallow['total_errors']}")

# ── Test 2: Recursive ─────────────────────────────────────────────────
# Scans the folder and all subfolders inside it
# Point this at a folder that actually has subfolders inside it
print("\n=== Recursive Scan ===")
result_deep = scan_directory(path, recursive=True)

print(f"Scanned directory : {result_deep['scanned_directory']}")
print(f"Total files found : {result_deep['total_files_found']}")
print(f"Total errors      : {result_deep['total_errors']}")

# The file count in Test 2 should be >= Test 1
# If both numbers are the same, your Desktop has no subfolders
# In that case point recursive scan at a different folder that has subfolders

# ── Print sample output from recursive scan ───────────────────────────
print("\n=== First 3 files from recursive scan ===")
for file in result_deep['files'][:3]:
    print(json.dumps(file, indent=2))

# ── Print errors if any ───────────────────────────────────────────────
if result_deep['errors']:
    print("\n=== Errors ===")
    for error in result_deep['errors']:
        print(error)