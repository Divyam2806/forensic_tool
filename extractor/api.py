"""
api.py — FastAPI REST Service
------------------------------
Exposes Python forensic modules as HTTP endpoints.
Java Swing GUI communicates with this service via HTTP requests.

Start service:
    uvicorn api:app --host 127.0.0.1 --port 8000

Architecture:
    Stateful — results stored in memory keyed by session_id.
    session_id created by /scan, passed to /browser and /report.
    Sessions persist until /clear called or service restarts.

Session lifecycle:
    /scan    → creates session, stores scan + manifest, exports to metadata-json/
    /browser → adds browser artifacts to existing session
    /report  → generates PDF from session data, saves to output/
    /clear   → removes session from memory
"""

import sys
import uuid
import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

app = FastAPI(
    title="Forensic Tool API",
    description="REST interface for forensic evidence extraction modules",
    version="1.0.0"
)

# ── Paths ──────────────────────────────────────────────────────────────
SOLR_PATH   = Path(__file__).parent.parent / "metadata-json"
OUTPUT_PATH = Path(__file__).parent / "output"

# ── In-memory session store ────────────────────────────────────────────
# Key: session_id (UUID string)
# Value: {
#     "scan":    combine_metadata() result,
#     "manifest": hash_directory_manifest() result,
#     "browser": extract_network_artifacts() result or None,
#     "created": timestamp string
# }
sessions: dict = {}


# ── Request models ─────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    path:      str
    max_files: int  = 1000
    recursive: bool = True
    output_folder: str = None

class BrowserRequest(BaseModel):
    session_id: str
    path:       str

class ReportRequest(BaseModel):
    session_id:   str
    top_n:        int = 10
    investigator: str = "Unknown"
    output_path: str = None

class AiAnalysisRequest(BaseModel):
    file_path: str

class ClearRequest(BaseModel):
    session_id: str


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/status")
def status():
    """Health check — Java calls on startup to confirm service running."""
    return {"status": "running", "service": "forensic-tool-api"}


@app.post("/scan")
def scan(request: ScanRequest):
    """
    Run fs + file metadata extraction on given path.
    Creates a new session, stores results in memory.
    Also exports file records to metadata-json/ for Solr indexing.
    Returns session_id — Java must store this for subsequent calls.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from main import combine_metadata, export_for_indexing
    from modules.hashing import hash_directory_manifest

    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    # Run scan
    result = combine_metadata(
        str(path),
        recursive=request.recursive,
        max_files=request.max_files
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # Compute manifest — mirrors ScanWorker behavior exactly
    manifest = hash_directory_manifest(str(path))

    # Export to output folder (default to SOLR_PATH)
    export_target = Path(request.output_folder) if request.output_folder else SOLR_PATH

    try:
        export_for_indexing(result, output_folder=export_target)
    except Exception as e:
        print(f"[WARN] Solr export failed: {e}")

    # Create session
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "scan":     result,
        "manifest": manifest,
        "browser":  None,
        "created":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return JSONResponse(content={
        "status":        "success",
        "session_id":    session_id,
        "total_files":   result["total_files"],
        "scanned_path":  result["scanned_directory"],
        "manifest_hash": manifest.get("manifest_hash"),
    })


@app.post("/browser")
def browser(request: BrowserRequest):
    """
    Extract browser artifacts from given Network folder.
    Adds results to existing session identified by session_id.
    /scan must be called first to create the session.
    """
    from modules.browser_artifacts import extract_network_artifacts

    if request.session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id} — run /scan first"
        )

    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    result = extract_network_artifacts(str(path))

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # Add to existing session
    sessions[request.session_id]["browser"] = result

    return JSONResponse(content={
        "status":        "success",
        "session_id":    request.session_id,
        "total_cookies": result["total_cookies"],
        "nel_records":   result["reporting_nel"].get("total", 0),
        "ts_domains":    result["transport_security"].get("total", 0),
    })


@app.post("/report")
def report(request: ReportRequest):
    """
    Generate PDF report from session data.
    /scan must be called first. /browser is optional.
    PDF saved to output/ with timestamped filename.
    """
    from modules.report_generator import generate_pdf_report

    if request.session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id} — run /scan first"
        )

    session = sessions[request.session_id]

    # Auto-generate output path and case ID
    timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    case_id     = f"DF-{timestamp}"
    output_path =  request.output_path or str(OUTPUT_PATH / f"forensic_report_{timestamp}.pdf")

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    try:
        saved_path = generate_pdf_report(
            combined_data=session["scan"],
            output_path=output_path,
            browser_data=session["browser"],
            manifest_data=session["manifest"],
            case_id=case_id,
            investigator=request.investigator,
            top_n=request.top_n,
            scan_duration=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={
        "status":      "success",
        "session_id":  request.session_id,
        "report_path": saved_path,
        "case_id":     case_id,
    })


@app.post("/clear")
def clear(request: ClearRequest):
    """
    Remove session from memory.
    Call after investigation is complete to free memory.
    """
    if request.session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )

    del sessions[request.session_id]

    return JSONResponse(content={
        "status":     "success",
        "session_id": request.session_id,
        "message":    "Session cleared from memory",
    })

@app.post("/analyze")
def analyze(request: AiAnalysisRequest):
    import json as _json
    from model.model_interface import analyze_artifact, truncate_large_fields, EXCLUDE_FIELDS
    from model.embeddings import safe_process_artifact_for_embedding

    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")

    if file_path.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    # Read original metadata
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            metadata = _json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    # Run LLM analysis
    llm_result = analyze_artifact(truncate_large_fields(
        {k: v for k, v in metadata.items() if k not in EXCLUDE_FIELDS}
    ))

    if "error" in llm_result:
        raise HTTPException(status_code=500, detail=llm_result.get("raw_output", llm_result["error"]))

    # Merge LLM result into original metadata
    metadata["ai_analysis"] = llm_result

    # Re-embed combined metadata
    embedding_result = safe_process_artifact_for_embedding(metadata)
    metadata["artifact_embedding"] = embedding_result["embedding"]

    # Overwrite original file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            _json.dump(metadata, f, indent=2, default=str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

    return JSONResponse(content={
        "status":   "success",
        "file":     str(file_path),
        "ai_analysis": llm_result,
    })