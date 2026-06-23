import json
import sys
from pathlib import Path

sys.path.insert(0, '..')

from modules.browser_artifacts import extract_network_artifacts

COOKIES_FOLDER = Path(r"C:\Users\Asus\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Network")

result = extract_network_artifacts(str(COOKIES_FOLDER))

nps_test = False

print(f"Folder scanned  : {result['folder']}")
print(f"Total cookies   : {result['total_cookies']}")

# ── Cookies ────────────────────────────────────────────────────────────
print("\n=== Cookies ===")
for extraction in result['cookies']:
    print(f"Database  : {extraction['database']}")
    print(f"Browser   : {extraction.get('browser_type', 'unknown')}")
    print(f"Total     : {extraction.get('total', 0)}")
    if extraction.get('error'):
        print(f"Error     : {extraction['error']}")
    else:
        print("\nFirst 3 cookies:")
        for cookie in extraction['cookies'][:3]:
            print(json.dumps(cookie, indent=2))

# ── Transport Security ─────────────────────────────────────────────────
print("\n=== Transport Security ===")
ts = result['transport_security']
if ts.get('error'):
    print(f"Error   : {ts['error']}")
else:
    print(f"Total domains : {ts['total']}")
    if ts['total'] > 3:
        print("\nFirst 3 domains:")
        for domain in ts['domains'][:3]:
            print(json.dumps(domain, indent=2))

# ── Network Persistent State ───────────────────────────────────────────
#experimental feature, no standard pattern between network persistent files

if nps_test:
    print("\n=== Network Persistent State ===")
    nps = result['network_state']
    if nps.get('error'):
        print(f"Error : {nps['error']}")
    else:
        print(json.dumps(nps['data'], indent=2))

# ── Reporting and NEL ──────────────────────────────────────────────────
print("\n=== Reporting and NEL ===")
nel = result['reporting_nel']
if nel.get('error'):
    print(f"Error   : {nel['error']}")
else:
    print(f"Total records : {nel['total']}")
    print("\nFirst 3 records:")
    for record in nel['records'][:3]:
        print(json.dumps(record, indent=2))