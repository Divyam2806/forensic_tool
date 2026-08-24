# Forensic Evidence Preservation & Cyber Forensics Toolkit

A GUI-driven, case-managed digital forensics toolkit that takes an investigation from evidence acquisition to a searchable, reportable case file — with role-based access control, chain-of-custody logging, and local AI-assisted analysis built in.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Layout](#project-layout)
- [Requirements](#requirements)
- [Setup](#setup)
- [Running the Toolkit](#running-the-toolkit)
- [Authentication & Roles](#authentication--roles)
- [Typical Workflow](#typical-workflow)
- [Case Folder Structure](#case-folder-structure)
- [Core Actions](#core-actions)
- [Search Query Examples](#search-query-examples)
- [Cross-Platform Notes](#cross-platform-notes)
- [Files That Stay Local](#files-that-stay-local)
- [Launch Checklist](#launch-checklist)
- [Roadmap](#roadmap)

---

## Overview

This project is a GUI-based forensic toolkit built around:

- a Python extractor for metadata and PDF/text content
- a Java Swing dashboard for case management and workflow control
- Apache Lucene for keyword and metadata search
- a locally hosted LLM (Qwen2.5-3B), served via a Python FastAPI service, for AI-assisted case analysis

The current UI supports:

- Login
- Role-based access control
- Create/Open Case
- Acquire Evidence
- Create Disk Image
- Extract Metadata
- Index Files
- Search Evidence
- Generate Report
- Audit Logs
- AI Analysis

## Key Features

The toolkit helps you:

- collect evidence into a case folder
- extract file and PDF metadata
- search file content and metadata with Lucene
- generate PDF forensic reports
- log chain-of-custody activity
- run AI-assisted analysis over case data using a locally hosted LLM

## System Architecture

The toolkit is split into three cooperating layers:

- **Presentation & Control (Java Swing):** handles login, role-based access control, case creation, and drives every workflow action (acquisition, imaging, extraction, indexing, search, reporting, AI analysis) against the active case.
- **Extraction & AI Service (Python):** the Python extractor pulls metadata and text content from evidence files, and a FastAPI service (`extractor/api.py`, run via `uvicorn`) serves the locally hosted Qwen2.5-3B model for AI Analysis.
- **Search (Apache Lucene):** the Java layer compiles extracted metadata into a Lucene index for fast keyword and fielded search.

> **Important:** the Java app depends on the Python FastAPI service at runtime — it will show an error dialog and refuse to proceed if that service is not running. Always start the FastAPI service first (see [Running the Toolkit](#running-the-toolkit)).

Every action taken through the GUI is scoped to a single active case and written into that case's own folder tree, keeping evidence, derived metadata, search indices, reports, and logs isolated per investigation.

## Project Layout

> **Note (from the project maintainers):** this tree is **not up to date**. It does not yet reflect `extractor/api.py` (the FastAPI service), the `model/` directory holding the local LLM weights, or the AI Analysis configuration in `config.properties`.

```text
forensic_tool/
├── extractor/
│   ├── main.py
│   ├── modules/
│   └── requirements.txt
│
├── lucene-forensic-search/
│   ├── pom.xml
│   ├── src/main/java/com/forensics/
│   ├── src/main/resources/users.json
│   └── cases/
│
├── evidence/              # source evidence files (can be a symlink)
├── metadata-json/         # generated metadata JSON files
├── index/                 # Lucene index
└── README.md
```

| Path | Purpose |
|---|---|
| `extractor/main.py` | Entry point for the Python metadata/content extractor |
| `extractor/api.py` | FastAPI service (started via `uvicorn api:app`) that the Java app calls for AI Analysis |
| `extractor/modules/` | Individual extraction modules invoked by `main.py` |
| `extractor/requirements.txt` | Python dependencies for the extractor and API service |
| `model/Qwen2.5-3B-Instruct.Q4_K_M.gguf` | Local LLM weights used for AI Analysis |
| `lucene-forensic-search/` | Java Swing GUI, case management, and Lucene search engine |
| `lucene-forensic-search/src/main/resources/users.json` | Sample login accounts and roles |
| `lucene-forensic-search/src/main/resources/config.properties` | ONNX model path and other local configuration |
| `lucene-forensic-search/cases/` | Root directory holding every case created through the GUI |
| `evidence/`, `metadata-json/`, `index/` | Top-level working directories referenced by the extractor and indexer |

## Requirements

- **Java 17+** — confirm with `java -version`
- **Maven 3.8+** — confirm with `mvn -version`
- **Python 3.13** with a virtualenv set up inside `extractor/`
- **Python dependencies** — from `extractor/`:
  ```bash
  python -m pip install -r requirements.txt
  ```
- **MediaInfo** — download from [mediaarea.net/en/MediaInfo](https://mediaarea.net/en/MediaInfo)
- **Qwen LLM model** — download [`Qwen2.5-3B-Instruct.Q4_K_M.gguf`](https://huggingface.co/divyam2806/qwen2.5-3b-forensic-finetuned) and place it at `model/Qwen2.5-3B-Instruct.Q4_K_M.gguf`
- **ONNX model path** — open `lucene-forensic-search/src/main/resources/config.properties` and update the ONNX model path present in root to match your local setup

## Setup

### Python Environment

Create and use a virtual environment for the extractor and API service:

```bash
cd forensic_tool/extractor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Additional Prerequisites

With the environment active, work through the [Requirements](#requirements) list above — install MediaInfo, download the Qwen model file to `model/Qwen2.5-3B-Instruct.Q4_K_M.gguf`, and update the ONNX model path in `config.properties`.

## Running the Toolkit

**Step 1 — Start the Python FastAPI service**

From the `extractor/` directory with your virtualenv active:

```bash
uvicorn api:app --host 127.0.0.1 --port 8000
```

Keep this terminal open — the Java app communicates with this service throughout its lifecycle. The app will show an error dialog and refuse to proceed if this service is not running.

**Step 2 — Build and run the Java app**

Open a new terminal, navigate to `lucene-forensic-search/` and run:

```bash
mvn compile exec:java -Dexec.mainClass=com.forensics.ForensicApp
```

**Step 3 — Login**

A login dialog will appear on launch. Use your registered credentials to proceed to the dashboard.

Admin account:

```text
user: admin
pass: admin123
```

## Authentication & Roles

### Default Login Users

These are the sample accounts in `src/main/resources/users.json`:

- `admin / admin123`
- `investigator / invest123`
- `analyst / analyst123`
- `auditor / audit123`

### Role Permissions

| Role | Permissions |
|---|---|
| **Admin** | Full access |
| **Investigator** | Create/open case, acquire evidence, create disk image, extract metadata, index files, search evidence, generate reports |
| **Analyst** | Open existing case, extract metadata, search evidence, generate reports |
| **Auditor** | View audit logs, search evidence |

## Typical Workflow

1. Start the Python FastAPI service (`uvicorn api:app ...`).
2. Launch the GUI.
3. Log in with a role.
4. Create or open a case.
5. Acquire evidence into the case.
6. Extract metadata.
7. Index the case metadata.
8. Search evidence.
9. Generate a report.

## Case Folder Structure

Each case is created under:

```text
lucene-forensic-search/cases/CASE001/
```

with subfolders like:

```text
evidence/
metadata/
index/
reports/
logs/
images/
```

**Note:** cases are stored under `lucene-forensic-search/cases/` by default. Metadata JSON exports generated by running the extractor from the CLI or the Python GUI (rather than through the Java case workflow) go to `forensic_tool/metadata-json/` for Lucene indexing instead.

## Core Actions

### Evidence Acquisition

The `Acquire Evidence` action copies a selected folder into the active case's:

```text
cases/<CASE_ID>/evidence/
```

It also logs chain-of-custody activity.

### Metadata Extraction & Indexing

The `Extract Metadata` action runs the Python extractor against the active case evidence folder and writes JSON into:

```text
cases/<CASE_ID>/metadata/
```

The `Index Files` action then indexes that metadata into:

```text
cases/<CASE_ID>/index/
```

### Search

The `Search Evidence` action opens a search dialog against the active case index.

### AI Analysis

The `AI Analysis` action uses the locally hosted Qwen2.5-3B model (served by the FastAPI service and configured via `config.properties`) to provide AI-assisted analysis of case data.

### Report Generation

The `Generate Report` action uses the existing Python report generator to create a PDF report from the active case and stores it in the case's `reports/` folder.

When you generate a report from the GUI, it is saved under:

```text
lucene-forensic-search/cases/<CASE_ID>/reports/
```

Example:

```text
lucene-forensic-search/cases/CASE001/reports/CASE001_report_20260708_035043.pdf
```

## Search Query Examples

From the GUI search box:

| Query | What it matches |
|---|---|
| `ganesh` | Free-text keyword search across indexed content |
| `extension:pdf` | Files with the `.pdf` extension |
| `modified:2026-06-22` | Files last modified on the given date |
| `author:ritik` | Documents whose author metadata is "ritik" |
| `encrypted:false` | Files that are not encrypted |

## Cross-Platform Notes

- The GUI, case management, metadata extraction, indexing, search, and report generation are designed to work across OSes as long as the required Java/Python dependencies are installed.
- Raw disk imaging currently uses `dd`, so that part is Unix-like system friendly and not fully Windows-native yet.

## Files That Stay Local

This repo ignores runtime forensic artifacts such as:

- `cases/`
- `evidence/`
- `metadata-json/`
- `index/`
- generated `.pdf` and `.img` files

So you can run the toolkit locally without pushing evidence artifacts to GitHub.

## Launch Checklist

If the GUI does not start, check:

- the Python FastAPI service (`uvicorn api:app ...`) is running on port 8000 before you start the Java app
- you ran Maven from `lucene-forensic-search/`
- Java 17 is installed
- the Python virtual environment exists in `extractor/.venv`
- `pypdf`, `reportlab`, and the other extractor dependencies are installed
- MediaInfo is installed
- the Qwen model file exists at `model/Qwen2.5-3B-Instruct.Q4_K_M.gguf`
- the ONNX model path in `config.properties` matches your local setup

## Roadmap

Planned future directions (not yet implemented):

- OCR support so text embedded in scanned/carved images can also be indexed and searched
- Low-level deleted-file recovery and signature-based file carving
- A distributed, multi-investigator web front end built on the existing case-and-auth service
- Cross-case correlation and comparison reporting
