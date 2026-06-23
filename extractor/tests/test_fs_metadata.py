import json
import sys

# Add the project root to path so Python can find the modules folder
sys.path.insert(0, '..')

from modules.fs_metadata import extract, scan_directory

# ── Test 1: Single file ────────────────────────────────────────────────
# Point this at any real file on your machine
# Change this path to something that actually exists on your laptop
result = extract(r"C:\Users\Asus\Desktop")
print(json.dumps(result, indent=2))