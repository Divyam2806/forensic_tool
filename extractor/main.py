import datetime
from pathlib import Path
from modules.fs_metadata import scan_directory
from modules.file_metadata import extract_from_directory
import json


def combine_metadata(path: str, recursive: bool = True, max_files=1000) -> list:
    """
    Run fs_metadata + file_metadata on same path.
    Merge results per file using 'path' as match key.
    Fields present in both (path, name) kept once.
    Module-specific fields combined into single dict per file.
    """
    fs_result   = scan_directory(path, recursive=recursive, max_files=max_files)
    file_result = extract_from_directory(path, recursive=recursive, max_files=max_files)

    if "error" in fs_result:
        return {"error": fs_result["error"]}
    if "error" in file_result:
        return {"error": file_result["error"]}

    # Index file_metadata results by path for fast lookup
    file_meta_by_path = {f["path"]: f for f in file_result["files"]}

    combined = []

    for fs_entry in fs_result["files"]:
        file_path = fs_entry["path"]
        file_entry = file_meta_by_path.get(file_path, {})

        # Start with fs_entry as base — has path, name already
        merged = dict(fs_entry)

        # Add file_metadata fields, skip duplicate keys (path, name)
        for key, value in file_entry.items():
            if key not in merged:
                merged[key] = value
            elif key in ("path", "name"):
                continue  # already present, skip duplicate
            else:
                # Key exists in both but isn't path/name — shouldn't
                # normally happen, but prefix to avoid silent overwrite
                merged[f"file_{key}"] = value

        combined.append(merged)

    return {
        "scanned_directory": fs_result["scanned_directory"],
        "total_files":       len(combined),
        "files":             combined,
    }

def export_for_indexing(combined_data: dict, output_folder: str = "../output/solr_index") -> int:
    """
    Write one JSON file per file-record for Solr indexing.
    Placeholder path — replace with actual Solr watch folder when known.
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f" DEBUG: Writing to {output_folder}")

    files = combined_data.get("files", [])
    count = 0

    for record in files:
        # Use file path hash or sanitized name as unique filename
        # to avoid collisions and invalid filename characters
        safe_name = record.get("name", f"record_{count}")
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in safe_name)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{safe_name}_{timestamp}.json"

        out_path = output_folder / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, default=str)

        count += 1

    return count

if __name__ == "__main__":
    import json
    import sys

    SOLR_PATH = Path(__file__).parent.parent/ 'metadata-json'
    FILE_SCAN_LIMIT = 5
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Starting scan: {path}")
    result = combine_metadata(path, max_files=FILE_SCAN_LIMIT)
    exported = export_for_indexing(result, output_folder=SOLR_PATH)
    print(f"Exported {exported} records for indexing")

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"Scanned directory : {result['scanned_directory']}")
    print(f"Total files found  : {result['total_files']}")
    print(f"\nShowing first {top_n} files:\n")

    for entry in result['files'][:top_n]:
        print(json.dumps(entry, indent=2, default=str))
        print("-" * 40)