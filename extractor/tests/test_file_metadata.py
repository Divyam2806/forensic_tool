import json
import sys
from pathlib import Path

sys.path.insert(0, '..')

from modules.file_metadata import extract_format_metadata

test_num = 1

# ── Point this at your test_samples folder ─────────────────────────────
SAMPLES_DIR = Path(__file__).parent.parent / 'sample_files'

# ── Supported extensions — one per format group ────────────────────────
SUPPORTED = {
    "PDF":   [".pdf"],
    "DOCX":  [".docx"],
    "XLSX":  [".xlsx"],
    "PPTX":  [".pptx"],
    "IMAGE": [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"],
    "HEIC":  [".heic"],
    "AUDIO": [ ".mp3", ".wav", ".flac", ".ogg", ".m4a"],
    "MEDIA": [".mp4", ".mov", ".avi", ".mkv", ".mp3"],
    "TEXT":  [".txt", ".csv", ".log"],
}

def get_format_group(extension: str) -> str:
    """Return the format group name for a given extension."""
    for group, extensions in SUPPORTED.items():
        if extension in extensions:
            return group
    return "UNKNOWN"


if test_num == 1:

    # ── Scan the samples folder ────────────────────────────────────────────
    if not SAMPLES_DIR.exists():
        print(f"[!] Samples directory not found: {SAMPLES_DIR}")
        sys.exit(1)

    # Group files by format
    grouped = {}
    unrecognised = []

    for file in SAMPLES_DIR.iterdir():
        if not file.is_file():
            continue
        ext   = file.suffix.lower()
        group = get_format_group(ext)
        if group == "UNKNOWN":
            unrecognised.append(file)
        else:
            grouped.setdefault(group, []).append(file)

    # ── Run extract_format_metadata on each file, grouped by format ─────────
    total_passed = 0
    total_failed = 0

    for group, files in grouped.items():
        print(f"\n{'='*60}")
        print(f" FORMAT GROUP: {group}")
        print(f"{'='*60}")

        for file in files:
            print(f"\n--- File: {file.name} ---")
            result = extract_format_metadata(str(file))

            if "error" in result:
                print(f"[FAILED] {result['error']}")
                total_failed += 1
            else:
                print(json.dumps(result, indent=2, default=str))
                total_passed += 1

    # ── Print unrecognised files ───────────────────────────────────────────
    if unrecognised:
        print(f"\n{'='*60}")
        print(f" UNRECOGNISED FORMATS")
        print(f"{'='*60}")
        for file in unrecognised:
            print(f"\n--- File: {file.name} ---")
            result = extract_format_metadata(str(file))
            print(json.dumps(result, indent=2, default=str))

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f" SUMMARY")
    print(f"{'='*60}")
    print(f"Total files found  : {total_passed + total_failed}")
    print(f"Successfully parsed: {total_passed}")
    print(f"Failed             : {total_failed}")
    print(f"Unrecognised       : {len(unrecognised)}")


elif test_num == 2:
    # ── Test extract_from_directory ────────────────────────────────────────
    from modules.file_metadata import extract_from_directory

    print(f"\n{'='*60}")
    print(f" TESTING extract_from_directory()")
    print(f"{'='*60}")

    # Non-recursive scan
    print("\n--- Non-Recursive ---")
    result_shallow = extract_from_directory(str(SAMPLES_DIR), recursive=False)
    print(f"Scanned directory : {result_shallow['scanned_directory']}")
    print(f"Total files found : {result_shallow['total_files_found']}")
    print(f"Total errors      : {result_shallow['total_errors']}")

    # Recursive scan
    print("\n--- Recursive ---")
    result_deep = extract_from_directory(str(SAMPLES_DIR), recursive=True)
    print(f"Scanned directory : {result_deep['scanned_directory']}")
    print(f"Total files found : {result_deep['total_files_found']}")
    print(f"Total errors      : {result_deep['total_errors']}")

    # Confirm counts match since sample_files has no subfolders
    if result_shallow['total_files_found'] == result_deep['total_files_found']:
        print("\n[OK] Recursive and non-recursive counts match — no subfolders in sample_files as expected")
    else:
        print("\n[OK] Recursive found more files — subfolders detected inside sample_files")

    # Print errors if any
    if result_deep['errors']:
        print("\n=== Errors ===")
        for error in result_deep['errors']:
            print(error)

    # Print first 3 results to verify data is actually being returned
    print("\n--- Sample of returned results ---")
    for file in result_deep['files'][:3]:
        print(json.dumps(file, indent=2, default=str))