import hashlib, json, time

def hash_file(path, algo="sha256", chunk_size=1024*1024):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

_log_initialized = False

def log_recovery(log_path, filename, method, offset, size, extra=None):
    global _log_initialized
    if not _log_initialized:
        open(log_path, "w").close()
        _log_initialized = True

    entry = {
        "timestamp": time.time(),
        "recovered_file": filename,
        "method": method,
        "source_offset": offset,
        "size": size,
        "extra": extra or {},
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")