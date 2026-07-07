from evidence_log import log_recovery
import hashlib
from collections import defaultdict
import os
from PIL import Image
import io

def try_validate_jpeg(data: bytes) -> bool:
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False

def estimate_jpeg_max_size(data: bytes, header_pos: int) -> int:
    pos = header_pos + 2
    while pos < len(data) - 9:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos+1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):  # SOF markers
            height = int.from_bytes(data[pos+5:pos+7], "big")
            width = int.from_bytes(data[pos+7:pos+9], "big")
            return width * height * 3  # worst-case uncompressed estimate
        seg_len = int.from_bytes(data[pos+2:pos+4], "big")
        pos += 2 + seg_len
    return 20 * 1024 * 1024  # fallback if SOF not found

def carve_with_gap(data: bytes, header: bytes, footer: bytes, start: int, max_gap_search=1024*1024*5):
    # header found at `start`, no footer within normal max_file_size
    # search wider range for footer, try skipping gap between two points
    search_region = data[start:start + max_gap_search]
    footer_positions = []
    pos = search_region.find(footer)
    while pos != -1:
        footer_positions.append(pos)
        pos = search_region.find(footer, pos + 1)

    for footer_pos in footer_positions:
        end = footer_pos + len(footer)
        candidate = data[start:start+end]
        if try_validate_jpeg(candidate):
            return candidate  # valid reconstruction found
    return None  # no valid fragment-spanning candidate found

SIGNATURES = {
    "jpg": (b"\xFF\xD8\xFF", b"\xFF\xD9"),
    "png": (b"\x89PNG\r\n\x1a\n", b"IEND\xaeB`\x82"),
    "pdf": (b"%PDF", b"%%EOF"),
}

def carve(img, out_dir, log_path, chunk_size=1024*1024*10, max_file_size=1024*1024*20, min_jpg_size=100*1024):
    total_size = img.get_size()
    offset = 0
    found_count = 0
    overlap = max_file_size
    carved_offsets = set()

    while offset < total_size:
        read_size = min(chunk_size + overlap, total_size - offset)
        data = img.read(offset, read_size)

        for ext, (header, footer) in SIGNATURES.items():
            start = data.find(header)
            while start != -1:
                abs_start = offset + start
                if abs_start in carved_offsets:
                    start = data.find(header, start + 1)
                    continue

                if ext == "jpg":
                    dynamic_max = estimate_jpeg_max_size(data, start)
                    start_search = start
                    chunk = None
                    while True:
                        end = data.find(footer, start_search)
                        if end == -1:
                            break
                        end += len(footer)
                        candidate = data[start:end]
                        if len(candidate) > dynamic_max:
                            break

                        # check for nested SOI between start+len(header) and this footer
                        nested_header_pos = data.find(header, start + len(header), end - len(footer))

                        if nested_header_pos != -1:
                            # nested thumbnail present, this footer likely belongs to it — skip past
                            start_search = end
                            continue

                        if try_validate_jpeg(candidate):
                            chunk = candidate
                            break
                        start_search = end

                    if chunk is None:
                        chunk = carve_with_gap(data, header, footer, start)
                        if chunk is None:
                            start = data.find(header, start + 1)
                            continue
                else:
                    end = data.find(footer, start)
                    if end == -1:
                        start = data.find(header, start + 1)
                        continue
                    end += len(footer)
                    if end - start > max_file_size:
                        start = data.find(header, start + 1)
                        continue
                    chunk = data[start:end]

                carved_offsets.add(abs_start)
                out_name = f"carved_{abs_start}.{ext}"
                with open(f"{out_dir}/{out_name}", "wb") as f:
                    f.write(chunk)
                log_recovery(log_path, out_name, "carving", abs_start, len(chunk))
                found_count += 1
                start = data.find(header, start + len(chunk))

        offset += chunk_size

    print(f"Carving done. {found_count} candidate files found.")

def dedup_by_hash(out_dir):
    size_groups = defaultdict(list)
    for fname in os.listdir(out_dir):
        path = os.path.join(out_dir, fname)
        size_groups[os.path.getsize(path)].append(path)

    removed = 0
    for size, paths in size_groups.items():
        if len(paths) < 2:
            continue  # unique size, no need to hash
        seen_hashes = {}
        for path in paths:
            with open(path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            if h in seen_hashes:
                os.remove(path)
                removed += 1
            else:
                seen_hashes[h] = path

    print(f"Dedup done. {removed} duplicate files removed.")

def merge_overlapping(out_dir, log_path):
    import json, os

    entries = []
    with open(log_path) as f:
        for line in f:
            entries.append(json.loads(line))

    carve_entries = [e for e in entries if e["method"] == "carving"]
    carve_entries.sort(key=lambda e: e["source_offset"])

    to_remove = set()
    for i in range(len(carve_entries)):
        for j in range(i+1, len(carve_entries)):
            a, b = carve_entries[i], carve_entries[j]
            a_end = a["source_offset"] + a["size"]
            b_end = b["source_offset"] + b["size"]
            if b["source_offset"] >= a_end:
                break  # sorted by offset, no further overlap possible
            overlap = min(a_end, b_end) - max(a["source_offset"], b["source_offset"])
            smaller = a if a["size"] < b["size"] else b
            if overlap > 0.7 * smaller["size"]:
                to_remove.add(smaller["recovered_file"])

    removed = 0
    for fname in to_remove:
        path = os.path.join(out_dir, fname)
        if os.path.exists(path):
            os.remove(path)
            removed += 1

    print(f"Merge done. {removed} overlapping duplicates removed.")