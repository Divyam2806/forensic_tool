import pytsk3, os
from evidence_log import log_recovery

def walk_and_recover(fs, out_dir, log_path, dir_obj=None, path=""):
    if dir_obj is None:
        dir_obj = fs.open_dir(path="/")
    for entry in dir_obj:
        if entry.info.name.name in (b".", b".."):
            continue
        name = entry.info.name.name.decode(errors="ignore")
        full_path = f"{path}/{name}"
        is_deleted = bool(entry.info.name.flags & pytsk3.TSK_FS_NAME_FLAG_UNALLOC)

        print(f"[SCAN] {full_path} deleted={is_deleted} meta={entry.info.meta}")

        if is_deleted:
            if entry.info.meta:
                recover_file(entry, full_path, out_dir, log_path)
            else:
                print(f"[SKIP] {full_path} deleted but meta missing (unrecoverable via Case A)")

        if entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
            try:
                walk_and_recover(fs, out_dir, log_path, entry.as_directory(), full_path)
            except Exception:
                pass

def recover_file(entry, name, out_dir, log_path):
    try:
        print("size:", entry.info.meta.size)
        print("addr (inode/cluster):", entry.info.meta.addr)
        print("flags:", entry.info.meta.flags)
        size = entry.info.meta.size
        data = entry.read_random(0, size)
        safe_name = name.strip("/").replace("/", "_")
        out_path = os.path.join(out_dir, safe_name)
        with open(out_path, "wb") as fh:
            fh.write(data)
        log_recovery(log_path, safe_name, "mft_deleted_entry", 0, size,
                     extra={"original_path": name, "inode": entry.info.meta.addr})
    except Exception as e:
        print(f"recover fail {name}: {e}")

RECORD_SIZE = 1024
SECTOR_SIZE = 512

def parse_attributes(record: bytes):
    attr_offset = int.from_bytes(record[20:22], "little")
    result = {"name": None, "parent_ref": None, "size": None, "resident": None, "data_runs": None}

    offset = attr_offset
    while offset < len(record) - 4:
        attr_type = int.from_bytes(record[offset:offset+4], "little")
        if attr_type == 0xFFFFFFFF:
            break

        attr_len = int.from_bytes(record[offset+4:offset+8], "little")
        if attr_len == 0:
            break

        non_resident_flag = record[offset+8]

        if attr_type == 0x30:  # $FILE_NAME
            content_offset_field = int.from_bytes(record[offset+20:offset+22], "little")
            content_start = offset + content_offset_field
            parent_ref = int.from_bytes(record[content_start:content_start+8], "little") & 0xFFFFFFFFFFFF
            name_len = record[content_start+64]
            name_offset = content_start + 66
            name_bytes = record[name_offset:name_offset + (name_len * 2)]
            name = name_bytes.decode("utf-16-le", errors="ignore")
            result["name"] = name
            result["parent_ref"] = parent_ref

        elif attr_type == 0x80:  # $DATA
            name_length = record[offset + 9]
            if name_length != 0:
                offset += attr_len
                continue  # skip named streams (ADS like Zone.Identifier)

            result["resident"] = (non_resident_flag == 0)
            if non_resident_flag == 0:
                content_size = int.from_bytes(record[offset+16:offset+20], "little")
                content_offset_field = int.from_bytes(record[offset+20:offset+22], "little")
                data_start = offset + content_offset_field
                result["size"] = content_size
                result["resident_data_offset"] = data_start  # relative to record start
            else:
                real_size = int.from_bytes(record[offset+48:offset+56], "little")
                runs_offset_field = int.from_bytes(record[offset+32:offset+34], "little")
                runs_start = offset + runs_offset_field
                result["size"] = real_size
                result["data_runs"] = decode_data_runs(record[runs_start:offset+attr_len])

        offset += attr_len

    return result

def decode_data_runs(run_bytes: bytes):
    runs = []
    i = 0
    prev_lcn = 0
    while i < len(run_bytes):
        header = run_bytes[i]
        if header == 0:
            break
        length_size = header & 0x0F
        offset_size = (header >> 4) & 0x0F
        i += 1

        length = int.from_bytes(run_bytes[i:i+length_size], "little")
        i += length_size

        offset_bytes = run_bytes[i:i+offset_size]
        i += offset_size
        offset_val = int.from_bytes(offset_bytes, "little", signed=True) if offset_size else 0

        lcn = prev_lcn + offset_val
        prev_lcn = lcn
        runs.append((lcn, length))

    return runs

def apply_fixup(record: bytearray):
    # fixup offset (2 bytes) at record[4:6], fixup count (2 bytes) at record[6:8]
    fixup_offset = int.from_bytes(record[4:6], "little")
    fixup_count = int.from_bytes(record[6:8], "little")

    if fixup_offset == 0 or fixup_count == 0:
        return record  # malformed/empty, skip fixup

    fixup_array = record[fixup_offset:fixup_offset + (fixup_count * 2)]

    for i in range(1, fixup_count):
        sector_end = (i * SECTOR_SIZE)
        if sector_end + 2 > len(record):
            break
        # last 2 bytes of each sector should match signature before patch
        replacement = fixup_array[i*2:i*2+2]
        record[sector_end-2:sector_end] = replacement

    return record

def extract_data_runs(img, data_runs, real_size, cluster_size, partition_offset):
    chunks = []
    for lcn, length in data_runs:
        offset = partition_offset + lcn * cluster_size
        size = length * cluster_size
        data = img.read(offset, size)
        chunks.append(data)
    full_data = b"".join(chunks)
    return full_data[:real_size]

def recover_mft_record(img, index, info, out_dir, log_path, cluster_size, partition_offset):
    try:
        if info["name"] is None or info["name"].startswith("$"):
            return  # skip system/unnamed records

        if info["resident"]:
            return  # resident data extraction not handled here yet, skip for now

        if not info["data_runs"]:
            return

        data = extract_data_runs(img, info["data_runs"], info["size"], cluster_size, partition_offset)
        safe_name = f"mft_{index}_{info['name']}"
        out_path = os.path.join(out_dir, safe_name)
        with open(out_path, "wb") as fh:
            fh.write(data)

        log_recovery(log_path, safe_name, "mft_raw_record", info["data_runs"][0][0], info["size"],
                     extra={"mft_index": index, "original_name": info["name"]})
        print(f"[RECOVERED] {safe_name} ({info['size']} bytes)")
    except Exception as e:
        print(f"recover fail index={index} name={info.get('name')}: {e}")

def scan_mft_deleted_records(fs, img, partition_offset):
    mft_file = fs.open_meta(inode=0)
    size = mft_file.info.meta.size
    mft_data = mft_file.read_random(0, size)

    deleted_addrs = []
    total_records = size // RECORD_SIZE

    for i in range(total_records):
        offset = i * RECORD_SIZE
        record = bytearray(mft_data[offset:offset + RECORD_SIZE])

        if record[:4] != b"FILE":
            continue

        record = apply_fixup(record)

        flags = int.from_bytes(record[22:24], "little")
        in_use = flags & 0x01

        if not in_use:
            deleted_addrs.append(i)
            info = parse_attributes(bytes(record))
            recover_mft_record(img, i, info, "recovered", "recovery_log.jsonl", fs.info.block_size, partition_offset)
            print(
                f"[MFT DELETED RECORD] index={i} name={info['name']} size={info['size']} resident={info['resident']} runs={info['data_runs']}")

    print(f"Total deleted MFT records found: {len(deleted_addrs)}")
    return deleted_addrs

