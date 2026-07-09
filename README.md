# Forensic Evidence Preservation & Cyber Forensics Toolkit

This project is a GUI-based forensic toolkit built around:

- a Python extractor for metadata and PDF/text content
- a Java Swing dashboard for case management and workflow control
- Apache Lucene for keyword and metadata search

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

## What this project does

The toolkit helps you:

- collect evidence into a case folder
- extract file and PDF metadata
- search file content and metadata with Lucene
- generate PDF forensic reports
- log chain-of-custody activity

## Project layout

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

## Requirements

You need:

- Java 17+
- Maven 3.8+
- Python 3.10+

The extractor also expects these Python packages, which are listed in:

```text
extractor/requirements.txt
```

## Recommended setup

If you use the Python extractor directly, create and use a virtual environment:

```bash
cd forensic_tool/extractor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the GUI

The GUI lives in the Lucene project.

```bash
cd forensic_tool/lucene-forensic-search
mvn exec:java -Dexec.mainClass="com.forensics.ForensicApp"
```

## Default login users

These are the sample accounts in `src/main/resources/users.json`:

- `admin / admin123`
- `investigator / invest123`
- `analyst / analyst123`
- `auditor / audit123`

## Roles

### Admin

- full access

### Investigator

- create/open case
- acquire evidence
- create disk image
- extract metadata
- index files
- search evidence
- generate reports

### Analyst

- open existing case
- extract metadata
- search evidence
- generate reports

### Auditor

- view audit logs
- search evidence

## Typical workflow

1. Launch the GUI.
2. Log in with a role.
3. Create or open a case.
4. Acquire evidence into the case.
5. Extract metadata.
6. Index the case metadata.
7. Search evidence.
8. Generate a report.

## Case folder structure

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

## Generated reports

When you generate a report from the GUI, it is saved under:

```text
lucene-forensic-search/cases/<CASE_ID>/reports/
```

Example:

```text
lucene-forensic-search/cases/CASE001/reports/CASE001_report_20260708_035043.pdf
```

## Evidence acquisition

The `Acquire Evidence` action copies a selected folder into the active case’s:

```text
cases/<CASE_ID>/evidence/
```

It also logs chain-of-custody activity.

## Metadata extraction and search

The `Extract Metadata` action runs the Python extractor against the active case evidence folder and writes JSON into:

```text
cases/<CASE_ID>/metadata/
```

The `Index Files` action then indexes that metadata into:

```text
cases/<CASE_ID>/index/
```

The `Search Evidence` action opens a search dialog against the active case index.

## Report generation

The `Generate Report` action uses the existing Python report generator to create a PDF report from the active case and stores it in the case’s `reports/` folder.

## Notes on cross-platform behavior

- The GUI, case management, metadata extraction, indexing, search, and report generation are designed to work across OSes as long as the required Java/Python dependencies are installed.
- Raw disk imaging currently uses `dd`, so that part is Unix-like system friendly and not fully Windows-native yet.

## Files that stay local

This repo ignores runtime forensic artifacts such as:

- `cases/`
- `evidence/`
- `metadata-json/`
- `index/`
- generated `.pdf` and `.img` files

So you can run the toolkit locally without pushing evidence artifacts to GitHub.

## Search examples

From the GUI search box:

```text
ganesh
```

```text
extension:pdf
```

```text
modified:2026-06-22
```

```text
author:ritik
```

```text
encrypted:false
```

## Launch checklist

If the GUI does not start, check:

- you ran Maven from `lucene-forensic-search/`
- Java 17 is installed
- the Python virtual environment exists in `extractor/.venv`
- `pypdf`, `reportlab`, and the other extractor dependencies are installed

