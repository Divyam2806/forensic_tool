from adapters import get_img_info, get_fs_info
from mft import walk_and_recover
from evidence_log import hash_file
import os, pytsk3

SOURCE = "nps-2009-canon2-gen4.E01"
OUT_DIR = "recovered"
LOG_PATH = "recovery_log.jsonl"

os.makedirs(OUT_DIR, exist_ok=True)

print("Source hash:", hash_file(SOURCE))

img = get_img_info(SOURCE)
print("Reported media size (bytes):", img.get_size())
fs, partition_offset = get_fs_info(img)
print("Partition offset:", partition_offset)

try:
    root = fs.open_dir(path="/")
    print("Root dir opened OK")
except Exception as e:
    print("Root dir open FAILED:", e)

walk_and_recover(fs, OUT_DIR, LOG_PATH)

from mft import scan_mft_deleted_records
fs_type = fs.info.ftype
if fs_type in (pytsk3.TSK_FS_TYPE_NTFS, pytsk3.TSK_FS_TYPE_NTFS_DETECT):
    scan_mft_deleted_records(fs, img, partition_offset)
else:
    print("Case C skipped: not NTFS, use Case A + carving for this filesystem")

from carving import carve, dedup_by_hash, merge_overlapping
carve(img, "recovered", log_path=LOG_PATH)
dedup_by_hash("recovered")
merge_overlapping("recovered", "recovery_log.jsonl")
