import hashlib
from pathlib import Path


def hash_file(path: str, chunk_size: int = 65536) -> dict:
    """
    Compute SHA-256 hash of a single file's full content.

    Args:
        path: Path to the file
        chunk_size: Bytes read per iteration — reading in chunks
                    avoids loading entire large files (e.g. videos)
                    into memory at once

    Returns:
        Dict with path, name, sha256 hash, and any error encountered
    """
    path = Path(path).resolve()

    if not path.exists():
        return {"error": f"Path does not exist: {path}"}

    if not path.is_file():
        return {"error": f"Not a file: {path}"}

    result = {
        "path":   str(path),
        "name":   path.name,
        "sha256": None,
        "error":  None,
    }

    try:
        sha256 = hashlib.sha256()

        with open(path, "rb") as f:
            # Read in chunks rather than f.read() all at once —
            # full-file hashing is correct forensically, but loading
            # a multi-GB video file entirely into memory would be
            # wasteful and could crash on low-memory machines
            while chunk := f.read(chunk_size):
                sha256.update(chunk)

        result["sha256"] = sha256.hexdigest()

    except PermissionError:
        result["error"] = "Permission denied"
    except Exception as e:
        result["error"] = str(e)

    return result


def hash_directory(directory: str, recursive: bool = True, max_files: int = 1000) -> dict:
    """
    Walk a directory and compute SHA-256 hash for every file found.
    Same pattern as scan_directory/extract_from_directory —
    hash_file() is the atomic unit, this just loops over files.
    """
    directory = Path(directory).resolve()

    if not directory.exists():
        return {"error": f"Directory does not exist: {directory}"}

    results = []
    errors  = []
    count   = 0

    walk = directory.rglob("*") if recursive else directory.glob("*")

    for item in walk:
        if count >= max_files:
            print(f"[!] Reached max_files limit ({max_files}). Stopping.")
            break
        if item.is_file():
            hashed = hash_file(str(item))
            if hashed.get("error"):
                errors.append(hashed)
            else:
                results.append(hashed)
            count += 1

    return {
        "hashed_directory":   str(directory),
        "total_files_hashed": len(results),
        "total_errors":       len(errors),
        "hashes":             results,
        "errors":             errors,
    }

def hash_directory_manifest(directory: str, recursive: bool = True, max_files: int = 1000) -> dict:
    """
    Compute a single SHA-256 hash over a manifest of the directory's
    file listing — filename, size, and modification time for each file.
    """
    directory = Path(directory).resolve()

    if not directory.exists():
        return {"error": f"Directory does not exist: {directory}"}

    manifest_lines = []
    file_count = 0
    errors = []

    walk = directory.rglob("*") if recursive else directory.glob("*")

    # Sort for deterministic ordering — same folder contents should
    # always produce the same manifest hash regardless of OS
    # traversal order
    items = sorted(walk, key=lambda p: str(p))

    for item in items:
        if file_count >= max_files:
            break
        if not item.is_file():
            continue

        try:
            stat = item.stat()
            manifest_lines.append(
                f"{item.name}|{stat.st_size}|{int(stat.st_mtime)}"
            )
            file_count += 1
        except Exception as e:
            errors.append({"path": str(item), "error": str(e)})

    manifest_string = "\n".join(manifest_lines)
    manifest_hash = hashlib.sha256(manifest_string.encode("utf-8")).hexdigest()

    return {
        "directory":      str(directory),
        "manifest_hash":  manifest_hash,
        "files_included": file_count,
        "total_errors":   len(errors),
        "errors":         errors
    }