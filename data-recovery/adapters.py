import pytsk3
import pyewf
import os

E01_SIGNATURE = b"\x45\x56\x46\x09\x0D\x0A\xFF\x00"  # "EVF" magic bytes

def detect_source_type(source_path: str) -> str:
    # block device paths - can't read signature same way, rely on path pattern
    if source_path.startswith(r"\\.\ ") or source_path.startswith(" /dev/ ") :
        return "live"

    ext = os.path.splitext(source_path)[1].lower()

    # confirm via magic bytes when it's a regular file
    if os.path.isfile(source_path):
        with open(source_path, "rb") as f:
            header = f.read(8)
        if header == E01_SIGNATURE:
            return "e01"
        return "raw"

    # fallback if signature check not possible (e.g. path doesn't exist yet)
    if ext == ".e01":
        return "e01"
    return "raw"

def get_img_info(source_path: str):
    source_type = detect_source_type(source_path)
    if source_type in ("raw", "live"):
        return pytsk3.Img_Info(source_path)
    elif source_type == "e01":
        filenames = pyewf.glob(source_path)
        ewf_handle = pyewf.handle()
        ewf_handle.open(filenames)
        return EwfImgInfo(ewf_handle)
    raise ValueError(f"unsupported source_type: {source_type}")

def detect_partition_offset(img):
    try:
        vol = pytsk3.Volume_Info(img)
    except Exception:
        return 0  # no partition table, bare volume

    for part in vol:
        desc = part.desc.decode(errors="ignore") if isinstance(part.desc, bytes) else part.desc
        if "Unallocated" in desc or "Primary Table" in desc or "Extended" in desc:
            continue
        return part.start * 512

    return 0  # fallback if nothing matched

def get_fs_info(img_info, fstype=None):
    offset = detect_partition_offset(img_info)
    if fstype:
        fs = pytsk3.FS_Info(img_info, offset=offset, type=fstype)
    else:
        fs = pytsk3.FS_Info(img_info, offset=offset)
    return fs, offset

class EwfImgInfo(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf = ewf_handle
        super().__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def read(self, offset, size):

        #DEBUG print(f"[EwfImgInfo.read] offset={offset} size={size}")

        self._ewf.seek(offset)
        data = self._ewf.read(size)

        #DEBUG print(f"[EwfImgInfo.read] got {len(data)} bytes, first 8: {data[:8]}")

        return data

    def get_size(self):
        return self._ewf.get_media_size()