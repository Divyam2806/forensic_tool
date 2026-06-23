import os
import json
import shutil
import sqlite3
import tempfile
import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# Timestamp converters
# ─────────────────────────────────────────────

def _chromium_time_to_utc(timestamp: int) -> str:
    """
    Chrome stores timestamps as microseconds since 1601-01-01.
    This is Windows FILETIME format, not Unix epoch.
    We subtract the difference between 1601 and 1970 (in seconds)
    to convert to a standard Unix timestamp.
    """
    try:
        if not timestamp or timestamp == 0:
            return "unavailable"
        unix_ts = timestamp / 1_000_000 - 11644473600
        return datetime.datetime.utcfromtimestamp(unix_ts).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except:
        return "unavailable"


def _firefox_time_to_utc(timestamp: int) -> str:
    """
    Firefox stores timestamps as microseconds since Unix epoch (1970-01-01).
    Simpler than Chrome — just divide by 1,000,000.
    """
    try:
        if not timestamp or timestamp == 0:
            return "unavailable"
        unix_ts = timestamp / 1_000_000
        return datetime.datetime.utcfromtimestamp(unix_ts).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except:
        return "unavailable"


# ─────────────────────────────────────────────
# DPAPI + AES-256-GCM decryption for Chromium
# ─────────────────────────────────────────────

def _get_chromium_decryption_key(cookies_folder: Path):
    """
    Chromium browsers store an AES-256 key in a file called "Local State"
    which sits in the User Data folder — two levels above the profile folder.

    Structure:
        User Data/
        ├── Local State       ← encrypted AES key lives here
        ├── Default/
        │   └── Network/
        │       └── Cookies   ← this is what we were given
        └── Profile 1/
            └── Network/
                └── Cookies

    We walk upward from the given folder looking for "Local State"
    since we don't know how deep the input folder is.
    """
    try:
        import base64

        # Walk up the directory tree looking for Local State
        # Stop after 5 levels to avoid walking too far up
        search_path = cookies_folder
        local_state_path = None

        for _ in range(5):
            candidate = search_path / "Local State"
            if candidate.exists():
                local_state_path = candidate
                break
            search_path = search_path.parent

        if not local_state_path:
            return None

        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)

        # The AES key is base64-encoded and DPAPI-encrypted
        encrypted_key = base64.b64decode(
            local_state["os_crypt"]["encrypted_key"]
        )

        # First 5 bytes are the literal string "DPAPI" — strip them
        encrypted_key = encrypted_key[5:]

        # Decrypt using Windows DPAPI via ctypes
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))
            ]

        input_blob = DATA_BLOB(
            len(encrypted_key),
            ctypes.cast(
                ctypes.c_char_p(encrypted_key),
                ctypes.POINTER(ctypes.c_char)
            )
        )
        output_blob = DATA_BLOB()

        success = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None, None, None, None, 0,
            ctypes.byref(output_blob)
        )

        if not success:
            return None

        key = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)
        return key

    except Exception:
        return None


def _decrypt_chromium_value(encrypted_value: bytes, key: bytes) -> str:
    """
    Decrypt a single Chromium cookie value.

    Modern Chrome (v80+) uses AES-256-GCM with a version prefix:
        Bytes 0-2  : version tag — b"v10" or b"v11"
        Bytes 3-14 : 12-byte nonce
        Bytes 15+  : ciphertext + 16-byte GCM auth tag at the end

    Older Chrome used raw DPAPI on the value directly — no prefix.
    """
    try:
        from Crypto.Cipher import AES

        if encrypted_value[:3] in (b"v10", b"v11"):
            nonce      = encrypted_value[3:15]
            ciphertext = encrypted_value[15:]
            cipher     = AES.new(key, AES.MODE_GCM, nonce=nonce)
            # Last 16 bytes are the GCM auth tag — strip them
            return cipher.decrypt(ciphertext)[:-16].decode("utf-8", errors="replace")
        else:
            # Legacy DPAPI-only encryption
            import ctypes
            import ctypes.wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ("cbData", ctypes.wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))
                ]

            input_blob = DATA_BLOB(
                len(encrypted_value),
                ctypes.cast(
                    ctypes.c_char_p(encrypted_value),
                    ctypes.POINTER(ctypes.c_char)
                )
            )
            output_blob = DATA_BLOB()

            ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(input_blob),
                None, None, None, None, 0,
                ctypes.byref(output_blob)
            )
            result = ctypes.string_at(output_blob.pbData, output_blob.cbData)
            ctypes.windll.kernel32.LocalFree(output_blob.pbData)
            return result.decode("utf-8", errors="replace")

    except Exception:
        return "[encrypted — DPAPI key unavailable]"


# ─────────────────────────────────────────────
# Database copy helper
# Browsers lock their SQLite files while running.
# We always copy to a temp file before reading.
# This is standard practice in forensic tools —
# Autopsy does the same thing internally.
# ─────────────────────────────────────────────

def _copy_to_temp(db_path: Path) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp_path = tmp.name
    shutil.copy2(str(db_path), tmp_path)
    return tmp_path


# ─────────────────────────────────────────────
# Chromium cookie extractor
# ─────────────────────────────────────────────

def _extract_chromium_cookies(db_path: Path, cookies_folder: Path) -> dict:
    """
    Extract all cookies from a Chromium Cookies database.
    Attempts DPAPI decryption on cookie values automatically.
    """
    result = {
        "database":     str(db_path),
        "browser_type": "Chromium-based (Chrome / Edge / Brave / Opera)",
        "cookies":      [],
        "total":        0,
        "error":        None,
    }

    # tmp_path = None

    try:
        # Get decryption key — walk up from cookies_folder to find Local State
        decryption_key = _get_chromium_decryption_key(cookies_folder)

        conn = sqlite3.connect(str(db_path))
        cursor   = conn.cursor()

        # Fetch every column available in the cookies table
        cursor.execute("""
            SELECT
                name,
                host_key,
                path,
                encrypted_value,
                expires_utc,
                creation_utc,
                last_access_utc,
                is_secure,
                is_httponly,
                samesite,
                has_expires,
                is_persistent,
                priority,
                source_scheme
            FROM cookies
            ORDER BY creation_utc DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            (name, host, path, enc_value, expires, created,
             last_access, is_secure, is_httponly, samesite,
             has_expires, is_persistent, priority, source_scheme) = row

            # Attempt decryption
            if decryption_key and enc_value:
                value = _decrypt_chromium_value(enc_value, decryption_key)
            elif enc_value:
                value = "[encrypted — DPAPI key unavailable]"
            else:
                value = ""

            result["cookies"].append({
                "name":          name,
                "domain":        host,
                "path":          path,
                "value":         value,
                "created":       _chromium_time_to_utc(created),
                "expires":       _chromium_time_to_utc(expires) if has_expires else "session",
                "last_accessed": _chromium_time_to_utc(last_access),
                "secure":        bool(is_secure),
                "httponly":      bool(is_httponly),
                "samesite":      samesite,
                "persistent":    bool(is_persistent),
                "priority":      priority,
                "source_scheme": source_scheme,
            })

        result["total"] = len(result["cookies"])

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────
# Firefox cookie extractor
# ─────────────────────────────────────────────

def _extract_firefox_cookies(db_path: Path) -> dict:
    """
    Extract all cookies from a Firefox cookies.sqlite database.
    Firefox stores cookie values in plaintext — no decryption needed.
    """
    result = {
        "database":     str(db_path),
        "browser_type": "Firefox",
        "cookies":      [],
        "total":        0,
        "error":        None,
    }

    try:
        conn = sqlite3.connect(str(db_path))
        cursor   = conn.cursor()

        cursor.execute("""
            SELECT
                name,
                host,
                path,
                value,
                expiry,
                creationTime,
                lastAccessed,
                isSecure,
                isHttpOnly,
                sameSite,
                rawSameSite,
                schemeMap
            FROM moz_cookies
            ORDER BY creationTime DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            (name, host, path, value, expiry, created,
             last_accessed, is_secure, is_httponly,
             samesite, raw_samesite, scheme_map) = row

            result["cookies"].append({
                "name":          name,
                "domain":        host,
                "path":          path,
                "value":         value,   # Plaintext in Firefox
                "created":       _firefox_time_to_utc(created),
                "expires":       (
                    datetime.datetime.utcfromtimestamp(expiry).strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    ) if expiry else "session"
                ),
                "last_accessed": _firefox_time_to_utc(last_accessed),
                "secure":        bool(is_secure),
                "httponly":      bool(is_httponly),
                "samesite":      samesite,
                "raw_samesite":  raw_samesite,
                "scheme_map":    scheme_map,
            })

        result["total"] = len(result["cookies"])

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────
# Database type detector
# Detects browser type from schema, not filename
# ─────────────────────────────────────────────

def _detect_database_type(db_path: Path) -> str:
    """
    Detect whether a SQLite database is a Chromium or Firefox
    cookie database by inspecting its schema.

    Accepts a path to an already-copied temp file —
    does not make its own copy.
    """
    try:
        conn   = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0].lower() for row in cursor.fetchall()}
        conn.close()

        if "cookies" in tables:
            return "chromium"
        elif "moz_cookies" in tables:
            return "firefox"
        else:
            return "unknown"

    except Exception:
        return "unknown"

# ─────────────────────────────────────────────
# Transport Security extractor
# TransportSecurity is a JSON file storing every
# HTTPS domain the browser connected to.
# Forensically valuable because it persists even
# after the user clears cookies and history.
# ─────────────────────────────────────────────

def _extract_transport_security(folder_path: Path) -> dict:
    result = {
        "file":    str(folder_path / "TransportSecurity"),
        "domains": [],
        "total":   0,
        "error":   None,
    }

    try:
        ts_path = folder_path / "TransportSecurity"
        if not ts_path.exists():
            result["error"] = "TransportSecurity file not found"
            return result

        with open(ts_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        # Top level key is "sts" — list of HSTS records
        for record in data.get("sts", []):
            # Timestamps are Unix epoch floats — convert directly
            expiry = record.get("expiry", 0)
            try:
                expiry_str = datetime.datetime.utcfromtimestamp(
                    float(expiry)
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
            except:
                expiry_str = "unavailable"

            result["domains"].append({
                "domain":             record.get("host", "unavailable"),
                "expiry":             expiry_str,
                "include_subdomains": record.get("sts_include_subdomains", False),
                "mode":               record.get("mode", "unavailable"),
            })

        result["total"] = len(result["domains"])

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────
# Network Persistent State extractor
# Stores HSTS records and broader network state.
# Contains additional data beyond TransportSecurity
# including network quality estimates and settings.
# ─────────────────────────────────────────────

def _extract_network_persistent_state(folder_path: Path) -> dict:
    """
    Extract data from Network Persistent State.
    This file stores network-level configuration and state
    that persists across browser sessions.
    """
    result = {
        "file":  str(folder_path / "Network Persistent State"),
        "data":  {},
        "error": None,
    }

    try:
        nps_path = folder_path / "Network Persistent State"
        if not nps_path.exists():
            result["error"] = "Network Persistent State file not found"
            return result

        with open(nps_path, "r", encoding="utf-8", errors='replace') as f:
            data = json.load(f)

        # Extract the most forensically relevant sections
        # The full file contains many internal Chrome settings
        # we only pull what is meaningful for an investigation
        result["data"] = {
            "broken_alternative_services": data.get("net", {})
            .get("http_server_properties", {})
            .get("broken_alternative_services", []),
            "network_qualities": data.get("net", {})
            .get("network_qualities", {}),
        }

    except Exception as e:
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────
# Reporting and NEL extractor
# NEL = Network Error Logging
# Websites instruct browsers to log network errors
# and report them back. This file stores those logs.
# Reveals sites visited and network errors encountered.
# ─────────────────────────────────────────────

def _extract_reporting_nel(folder_path: Path) -> dict:
    result = {
        "file":    str(folder_path / "Reporting and NEL"),
        "records": [],
        "total":   0,
        "error":   None,
    }

    tmp_path = None
    try:
        nel_path = folder_path / "Reporting and NEL"
        if not nel_path.exists():
            result["error"] = "Reporting and NEL file not found"
            return result

        # This is a SQLite database, not JSON
        tmp_path = _copy_to_temp(nel_path)
        conn     = sqlite3.connect(tmp_path)
        cursor   = conn.cursor()

        # Extract reporting endpoints
        cursor.execute("""
            SELECT
                origin_scheme,
                origin_host,
                origin_port,
                group_name,
                is_include_subdomains,
                expires_us_since_epoch,
                last_access_us_since_epoch
            FROM reporting_endpoint_groups
        """)

        for row in cursor.fetchall():
            (scheme, host, port, group, include_subdomains,
             expires, last_access) = row

            result["records"].append({
                "type":               "reporting-endpoint-group",
                "origin":             f"{scheme}://{host}:{port}",
                "group_name":         group,
                "include_subdomains": bool(include_subdomains),
                "expires":            _chromium_time_to_utc(expires),
                "last_accessed":      _chromium_time_to_utc(last_access),
            })

        # Extract individual endpoints
        cursor.execute("""
            SELECT
                origin_scheme,
                origin_host,
                origin_port,
                group_name,
                url
            FROM reporting_endpoints
        """)

        for row in cursor.fetchall():
            scheme, host, port, group, url = row
            result["records"].append({
                "type":       "reporting-endpoint",
                "origin":     f"{scheme}://{host}:{port}",
                "group_name": group,
                "url":        url,
            })

        conn.close()
        result["total"] = len(result["records"])

    except Exception as e:
        result["error"] = str(e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return result

# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def extract_network_artifacts(folder_path: str) -> dict:
    """
    Given a Network folder path, extract all available artifacts:
    - Cookies (Chromium and Firefox)
    - TransportSecurity (HTTPS domains visited)
    - Network Persistent State (network configuration)
    - Reporting and NEL (network error logging)

    Args:
        folder_path: Path to the Network folder
                     e.g. Chrome  → ...Chrome/User Data/Default/Network
                          Firefox → ...Firefox/Profiles/xxxx.default

    Returns:
        Dict containing all extracted artifacts organized by type
    """
    folder_path = Path(folder_path).resolve()

    if not folder_path.exists():
        return {"error": f"Path does not exist: {folder_path}"}

    if not folder_path.is_dir():
        return {"error": f"Path is not a folder: {folder_path}"}

    result = {
        "folder":              str(folder_path),
        "cookies":             {},
        "transport_security":  {},
        "network_state":       {},
        "reporting_nel":       {},
        "total_cookies":       0,
    }

    # ── Cookies ───────────────────────────────────────────────────────
    KNOWN_COOKIE_FILES = ["Cookies", "cookies.sqlite"]
    cookie_extractions = []

    for filename in KNOWN_COOKIE_FILES:
        db_path = folder_path / filename
        if not db_path.exists():
            continue

        tmp_path = None
        try:
            tmp_path    = _copy_to_temp(db_path)
            tmp_as_path = Path(tmp_path)
            db_type     = _detect_database_type(tmp_as_path)

            if db_type == "chromium":
                extraction = _extract_chromium_cookies(
                    tmp_as_path, folder_path
                )
                extraction["database"] = str(db_path)
            elif db_type == "firefox":
                extraction = _extract_firefox_cookies(tmp_as_path)
                extraction["database"] = str(db_path)
            else:
                extraction = {
                    "database": str(db_path),
                    "error":    "Unrecognised schema",
                }

            cookie_extractions.append(extraction)
            result["total_cookies"] += extraction.get("total", 0)

        except Exception as e:
            cookie_extractions.append({
                "database": str(db_path),
                "error":    str(e),
            })
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    result["cookies"] = cookie_extractions

    # ── Additional network artifacts ──────────────────────────────────
    result["transport_security"] = _extract_transport_security(folder_path)
    result["network_state"]      = _extract_network_persistent_state(folder_path)
    result["reporting_nel"]      = _extract_reporting_nel(folder_path)

    return result


