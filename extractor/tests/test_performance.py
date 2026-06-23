import sys
import time

sys.path.insert(0, '..')

from main import combine_metadata

TARGET_PATH = r"C:\\"
MAX_FILES   = 1000  # safety cap, override in modules if needed

print(f"Starting scan: {TARGET_PATH}")
print("This may take a while depending on directory size...\n")

start_time = time.perf_counter()

result = combine_metadata(TARGET_PATH, True, MAX_FILES)

end_time = time.perf_counter()
elapsed  = end_time - start_time

if "error" in result:
    print(f"Error: {result['error']}")
    sys.exit(1)

print(f"Scanned directory : {result['scanned_directory']}")
print(f"Total files found  : {result['total_files']}")
print(f"Time taken          : {elapsed:.2f} seconds")
print(f"Avg time per file   : {(elapsed / result['total_files']) * 1000:.2f} ms"
      if result['total_files'] > 0 else "No files found")