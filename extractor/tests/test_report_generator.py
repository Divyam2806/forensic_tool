import sys
import time

sys.path.insert(0, '..')

from main import combine_metadata
from modules.browser_artifacts import extract_network_artifacts
from modules.report_generator import generate_pdf_report
from modules.hashing import hash_directory_manifest

# ── Config ──────────────────────────────────────────────────────────────
SCAN_PATH    = r"C:\Users\Asus\Documents"
BROWSER_PATH = r"C:\Users\Asus\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Network"

import datetime
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_PATH = f"../output/forensic_report_{timestamp}.pdf"
TOP_N        = 30

# ── Run fs + file metadata scan ─────────────────────────────────────────
print(f"Scanning: {SCAN_PATH}")
start = time.perf_counter()
combined = combine_metadata(SCAN_PATH)
duration = time.perf_counter() - start

if "error" in combined:
    print(f"Error: {combined['error']}")
    sys.exit(1)

print(f"Files found: {combined['total_files']} | Time: {duration:.2f}s")

# ── Run browser artifact extraction (optional) ─────────────────────────
browser_data = None
try:
    print(f"\nExtracting browser artifacts: {BROWSER_PATH}")
    browser_data = extract_network_artifacts(BROWSER_PATH)
    if "error" in browser_data:
        print(f"Browser extraction skipped: {browser_data['error']}")
        browser_data = None
    else:
        print(f"Cookies found: {browser_data.get('total_cookies', 0)}")
except Exception as e:
    print(f"Browser extraction failed: {e}")
    browser_data = None

# ── Generate report ──────────────────────────────────────────────────────
import datetime
manifest = hash_directory_manifest(SCAN_PATH)

print(f"\nGenerating PDF report...")
report_path = generate_pdf_report(
    combined_data=combined,
    output_path=OUTPUT_PATH,
    browser_data=browser_data,
    manifest_data=manifest,
    case_id = f"DF-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
    investigator="Divyam",
    top_n=TOP_N,
    scan_duration=duration,
)

print(f"Report saved: {report_path}")