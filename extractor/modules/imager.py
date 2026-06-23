import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone

import pyewf


CHUNK_SIZE = 1024 * 1024  # 1MB read/write chunks


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _size_human(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


# ---------------------------------------------------------------------------
# Device enumeration / write-block (Linux only — flag clearly if not Linux)
# ---------------------------------------------------------------------------

def list_devices():
    """List block devices. Linux: via lsblk. Returns list of dicts."""
    if platform.system() != "Linux":
        raise NotImplementedError(
            "list_devices() only implemented for Linux in this version. "
            "On Windows, use 'wmic diskdrive list brief' or "
            "'Get-PhysicalDisk' in PowerShell to find the device path."
        )
    result = subprocess.run(
        ["lsblk", "-J", "-o", "NAME,PATH,SIZE,MODEL,SERIAL,TYPE,RO"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return data.get("blockdevices", [])


def get_source_size_bytes(source_path):
    """Get size of a block device or regular file in bytes."""
    if os.path.isdir(source_path):
        raise ValueError("source_path is a directory; this module images block devices/files, not directories.")
    if platform.system() == "Linux" and source_path.startswith("/dev/"):
        result = subprocess.run(
            ["blockdev", "--getsize64", source_path],
            capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip())
    return os.path.getsize(source_path)


def is_read_only(device_path):
    """Check if a Linux block device is currently set read-only."""
    if platform.system() != "Linux":
        raise NotImplementedError("is_read_only() only implemented for Linux.")
    result = subprocess.run(
        ["blockdev", "--getro", device_path],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip() == "1"


def set_read_only(device_path):
    """Set a Linux block device to read-only. Requires root."""
    if platform.system() != "Linux":
        raise NotImplementedError("set_read_only() only implemented for Linux.")
    subprocess.run(["blockdev", "--setro", device_path], check=True)
    return is_read_only(device_path)


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

def acquire_to_e01(source_path, output_dir, case_id=None, examiner=None,
                    notes=None, progress_callback=None):
    """
    Stream source_path (block device or raw file) into a .E01 image.

    progress_callback(bytes_done, total_bytes) is called after every chunk,
    if provided.

    Returns path to the acquisition JSON sidecar.
    """
    os.makedirs(output_dir, exist_ok=True)

    case_id = case_id or datetime.now(timezone.utc).strftime("CASE-%Y%m%d-%H%M%S")
    image_base = os.path.join(output_dir, case_id)   # pyewf appends .E01 itself on write
    image_path = image_base + ".E01"
    acquisition_path = os.path.join(output_dir, f"{case_id}_acquisition.json")

    if os.path.exists(image_path):
        raise FileExistsError(f"image already exists: {image_path}")

    total_bytes = get_source_size_bytes(source_path)

    md5 = hashlib.md5()
    sha256 = hashlib.sha256()

    start_time = _now_iso()

    handle = pyewf.handle()
    try:
        handle.open([image_base], mode="w")
    except OSError as exc:
        raise RuntimeError(
            f"pyewf failed to open for write: {exc}. "
            "Most likely pyewf was compiled without zlib support — "
            "install via 'sudo apt install python3-libewf' or rebuild from "
            "source with zlib1g-dev present (see module docstring)."
        ) from exc

    bytes_done = 0
    try:
        with open(source_path, "rb") as src:
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                md5.update(chunk)
                sha256.update(chunk)
                bytes_done += len(chunk)
                if progress_callback:
                    progress_callback(bytes_done, total_bytes)
    finally:
        handle.close()

    end_time = _now_iso()

    image_size_bytes = os.path.getsize(image_path)

    acquisition = {
        "case_id": case_id,
        "examiner": examiner or "unavailable",
        "source_path": source_path,
        "source_size_bytes": total_bytes,
        "source_size_human": _size_human(total_bytes),
        "bytes_acquired": bytes_done,
        "acquisition_start": start_time,
        "acquisition_end": end_time,
        "acquisition_tool": "imager_e01.py",
        "acquisition_tool_version": "0.1.0",
        "platform": platform.system(),
        "image_format": "E01",
        "image_file": os.path.basename(image_path),
        "image_size_bytes": image_size_bytes,
        "image_size_human": _size_human(image_size_bytes),
        "hash_md5": md5.hexdigest(),
        "hash_sha256": sha256.hexdigest(),
        "verification_status": "not_verified",
        "complete": bytes_done == total_bytes,
        "notes": notes or "unavailable",
    }
    with open(acquisition_path, "w", encoding="utf-8") as f:
        json.dump(acquisition, f, indent=2)

    return acquisition_path


def verify_e01(image_path, expected_md5=None, expected_sha256=None, progress_callback=None):
    """
    Re-read an E01 image start to finish, recompute hashes, compare.
    Returns dict: {"md5_match": bool|None, "sha256_match": bool|None, "actual_md5":..., "actual_sha256":...}
    """
    segment_files = pyewf.glob(image_path)
    handle = pyewf.handle()
    handle.open(segment_files, mode="r")

    total = handle.get_media_size()
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()

    bytes_done = 0
    try:
        while bytes_done < total:
            to_read = min(CHUNK_SIZE, total - bytes_done)
            chunk = handle.read(to_read)
            if not chunk:
                break
            md5.update(chunk)
            sha256.update(chunk)
            bytes_done += len(chunk)
            if progress_callback:
                progress_callback(bytes_done, total)
    finally:
        handle.close()

    actual_md5 = md5.hexdigest()
    actual_sha256 = sha256.hexdigest()

    return {
        "actual_md5": actual_md5,
        "actual_sha256": actual_sha256,
        "bytes_read": bytes_done,
        "media_size": total,
        "md5_match": (actual_md5 == expected_md5) if expected_md5 else None,
        "sha256_match": (actual_sha256 == expected_sha256) if expected_sha256 else None,
    }


def verify_against_acquisition_json(image_path, acquisition_json_path):
    """Convenience: load expected hashes from the sidecar JSON, verify, update it."""
    with open(acquisition_json_path, "r", encoding="utf-8") as f:
        acquisition = json.load(f)

    result = verify_e01(
        image_path,
        expected_md5=acquisition.get("hash_md5"),
        expected_sha256=acquisition.get("hash_sha256"),
    )

    acquisition["verification_status"] = (
        "verified" if result["md5_match"] and result["sha256_match"] else "mismatch"
    )
    acquisition["verification_time"] = _now_iso()
    with open(acquisition_json_path, "w", encoding="utf-8") as f:
        json.dump(acquisition, f, indent=2)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="E01 forensic imaging tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List block devices (Linux)")

    p_acq = sub.add_parser("acquire", help="Image a device/file to E01")
    p_acq.add_argument("source", help="Source device or raw file path")
    p_acq.add_argument("-o", "--output-dir", default="./output")
    p_acq.add_argument("--case-id", default=None)
    p_acq.add_argument("--examiner", default=None)
    p_acq.add_argument("--notes", default=None)

    p_ver = sub.add_parser("verify", help="Verify an E01 against its acquisition JSON")
    p_ver.add_argument("image_path")
    p_ver.add_argument("acquisition_json")

    args = parser.parse_args()

    if args.command == "list":
        for dev in list_devices():
            print(dev)

    elif args.command == "acquire":
        def progress(done, total):
            pct = (done / total * 100) if total else 0
            print(f"\r{_size_human(done)} / {_size_human(total)} ({pct:.1f}%)", end="", flush=True)

        acquisition_path = acquire_to_e01(
            args.source, args.output_dir,
            case_id=args.case_id, examiner=args.examiner, notes=args.notes,
            progress_callback=progress,
        )
        print()
        print(f"Acquisition JSON: {acquisition_path}")

    elif args.command == "verify":
        result = verify_against_acquisition_json(args.image_path, args.acquisition_json)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()