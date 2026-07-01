import json
import sys
from pathlib import Path

sys.path.insert(0, '..')

from modules.hashing import hash_file, hash_directory, hash_directory_manifest

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "sample_files"

# ── Test 1: single file, run twice — confirm deterministic ─────────────
sample_file = next(SAMPLES_DIR.iterdir())  # grab first file in folder

print("=== Single File Hash (run twice for determinism check) ===")
result_1 = hash_file(str(sample_file))
result_2 = hash_file(str(sample_file))

print(json.dumps(result_1, indent=2))

if result_1["sha256"] == result_2["sha256"]:
    print("\n[OK] Hash matched on both runs — deterministic as expected")
else:
    print("\n[FAIL] Hash mismatch between runs — something is wrong")

# ── Test 2: directory hash ──────────────────────────────────────────────
print(f"\n=== Directory Hash: {SAMPLES_DIR} ===")
dir_result = hash_directory(str(SAMPLES_DIR), recursive=True)

print(f"Total files hashed : {dir_result['total_files_hashed']}")
print(f"Total errors       : {dir_result['total_errors']}")

print("\nFirst 3 hashes:")
for h in dir_result['hashes'][:3]:
    print(json.dumps(h, indent=2))

if dir_result['errors']:
    print("\n=== Errors ===")
    for e in dir_result['errors']:
        print(e)

# Test 3- hash manifest of directory
print(f"\n=== Directory Hash Manifest: {SAMPLES_DIR} ===")
dir_result = hash_directory_manifest(str(SAMPLES_DIR), recursive=True)
dir_result2 = hash_directory_manifest(str(SAMPLES_DIR), recursive=True)

if dir_result["manifest_hash"] == dir_result2["manifest_hash"]:
    print("\n[OK] Hash matched on both runs — deterministic as expected")
    print(f"\n Manifest hash : {dir_result['manifest_hash']}")

print(f"Total files hashed : {dir_result['files_included']}")
print(f"Total errors       : {dir_result['total_errors']}")

