import os
import stat
import platform
import datetime
from pathlib import Path


def _ts(epoch: float) -> str:
    """Convert a Unix epoch timestamp to a readable UTC string."""
    return datetime.datetime.utcfromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S UTC")


def _human_size(size_bytes: int) -> str:
    """Convert raw bytes to a human-readable size string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def _windows_attributes(path: str) -> dict:
    """
    Pull NTFS file attribute flags using ctypes.
    ctypes lets us call Windows API functions directly
    without any third party library.

    GetFileAttributesW returns a bitmask — each bit
    represents one attribute flag.
    """
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == -1:
            return {"error": "GetFileAttributesW failed — check path"}

        return {
            "readonly":   bool(attrs & 0x1),
            "hidden":     bool(attrs & 0x2),
            "system":     bool(attrs & 0x4),
            "archive":    bool(attrs & 0x20),   # Set every time the file is modified
                                                # Backup software uses this to track changes
            "encrypted":  bool(attrs & 0x4000), # Windows EFS encryption
            "compressed": bool(attrs & 0x800),  # NTFS-level compression
            "sparse":     bool(attrs & 0x200),  # Large file with mostly empty blocks
        }
    except Exception as e:
        return {"error": str(e)}


def _windows_mft_info(path: str) -> dict:
    """
    Retrieve the MFT (Master File Table) file index for this file.

    Every file on NTFS has one row in the MFT — a structured record
    that stores all metadata about the file. The file index is that
    row's number, and it uniquely identifies the file on this volume.

    We use GetFileInformationByHandle because Python's os.stat()
    does not expose the MFT index directly.
    """
    try:
        import ctypes
        import ctypes.wintypes

        handle = ctypes.windll.kernel32.CreateFileW(
            str(path),
            0x80000000,   # GENERIC_READ — open for reading only
            0x1,          # FILE_SHARE_READ — other processes can still read it
            None,         # No security attributes
            3,            # OPEN_EXISTING — fail if file doesn't exist
            0x02000000,   # FILE_FLAG_BACKUP_SEMANTICS — required to open directories
            None
        )

        INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value
        if handle == INVALID_HANDLE:
            return {"mft_file_index": "unavailable — access denied or non-NTFS volume"}

        # This C struct (windows sdk docs) maps exactly to what the Windows API fills
        class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes",     ctypes.wintypes.DWORD),
                ("ftCreationTime",       ctypes.wintypes.FILETIME),
                ("ftLastAccessTime",     ctypes.wintypes.FILETIME),
                ("ftLastWriteTime",      ctypes.wintypes.FILETIME),
                ("dwVolumeSerialNumber", ctypes.wintypes.DWORD),
                ("nFileSizeHigh",        ctypes.wintypes.DWORD),
                ("nFileSizeLow",         ctypes.wintypes.DWORD),
                ("nNumberOfLinks",       ctypes.wintypes.DWORD),
                ("nFileIndexHigh",       ctypes.wintypes.DWORD),
                ("nFileIndexLow",        ctypes.wintypes.DWORD),
            ]

        info = BY_HANDLE_FILE_INFORMATION()
        ctypes.windll.kernel32.GetFileInformationByHandle(handle, ctypes.byref(info))
        ctypes.windll.kernel32.CloseHandle(handle)

        # The file index is stored as two 32-bit integers (high and low)
        # Shift high left by 32 bits and OR with low to get the full 64-bit index
        file_index = (info.nFileIndexHigh << 32) | info.nFileIndexLow

        return {
            "mft_file_index":  file_index,
            "hard_link_count": info.nNumberOfLinks,
            "volume_serial":   hex(info.dwVolumeSerialNumber),
        }

    except Exception as e:
        return {"mft_file_index": f"error: {e}"}


def extract(path: str) -> dict:
    """
    Main function — given a file path, return all file system
    level metadata for that file as a dictionary.
    """
    path = Path(path).resolve()

    if not path.exists():
        return {"error": f"Path does not exist: {path}"}

    try:
        s = path.stat()
    except PermissionError:
        return {"error": f"Permission denied: {path}"}

    result = {
        "path":         str(path),
        "name":         path.name,
        "extension":    path.suffix.lower() if path.suffix else "[none]",
        "is_file":      path.is_file(),
        "is_directory": path.is_dir(),
        "is_symlink":   path.is_symlink(),
        "size_bytes":   s.st_size,
        "size_human":   _human_size(s.st_size),

        # ── MAC Times ─────────────────────────────────────────────────────
        # st_mtime — last time the file CONTENT was written to
        "time_modified": _ts(s.st_mtime),

        # st_atime — last time the file was READ
        # Important caveat: Windows often disables atime updates by default
        # (registry key: NtfsDisableLastAccessUpdate) for performance reasons
        # so this value may be stale or frozen on many Windows machines
        "time_accessed": _ts(s.st_atime),

        # st_ctime — means different things depending on OS (see module docstring)
        "time_ctime":    _ts(s.st_ctime),
        "ctime_meaning": (
            "file creation time (NTFS — stored in MFT)"
            if platform.system() == "Windows"
            else "inode change time — NOT creation time (ext4/Linux)"
        ),

        "platform":    platform.system(),
        "is_readable": os.access(path, os.R_OK),
        "is_writable": os.access(path, os.W_OK),
    }

    # ── Windows / NTFS specific fields ────────────────────────────────────
    if platform.system() == "Windows":
        result["ntfs_attributes"] = _windows_attributes(str(path))
        result["ntfs_mft_info"]   = _windows_mft_info(str(path))

    # ── Linux / macOS specific fields ─────────────────────────────────────
    else:
        result["inode"]       = s.st_ino
        result["uid"]         = s.st_uid
        result["gid"]         = s.st_gid
        result["permissions"] = stat.filemode(s.st_mode)
        result["mode_octal"]  = oct(s.st_mode)

    return result


def scan_directory(directory: str, recursive: bool = True, max_files: int = 1000) -> dict:
    """
    Walk a directory and call extract() on every file found.
    extract() is the atomic unit — this function just loops over files
    and collects the results.
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
            meta = extract(str(item))
            if "error" in meta:
                errors.append(meta)
            else:
                results.append(meta)
            count += 1

    return {
        "scanned_directory": str(directory),
        "total_files_found": len(results),
        "total_errors":      len(errors),
        "files":             results,
        "errors":            errors,
    }