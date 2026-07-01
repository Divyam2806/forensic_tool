
import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


def _build_header(story, styles, scanned_path: str, scan_duration: float = None):
    story.append(Paragraph("Digital Forensic Analysis Report", styles['Title']))
    story.append(Spacer(1, 12))

    meta_lines = [
        f"<b>Generated:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"<b>Path scanned:</b> {scanned_path}",
    ]
    if scan_duration is not None:
        meta_lines.append(f"<b>Scan duration:</b> {scan_duration:.2f} seconds")

    for line in meta_lines:
        story.append(Paragraph(line, styles['Normal']))
    story.append(Spacer(1, 20))


def _build_summary(story, styles, combined_data: dict, browser_data: dict = None):
    story.append(Paragraph("Executive Summary", styles['Heading1']))
    story.append(Spacer(1, 8))

    total_files = combined_data.get("total_files", 0)

    # Count format breakdown
    format_counts = {}
    error_count = 0
    gps_count = 0

    for f in combined_data.get("files", []):
        fmt = f.get("format", "unknown")
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
        if "error" in f:
            error_count += 1
        if f.get("gps_latitude") and f.get("gps_latitude") != "unavailable":
            gps_count += 1

    summary_data = [["Metric", "Value"], ["Total files scanned", str(total_files)],
                    ["Files with errors", str(error_count)], ["Files with GPS data", str(gps_count)]]

    for fmt, count in sorted(format_counts.items(), key=lambda x: -x[1]):
        summary_data.append([f"  Format: {fmt}", str(count)])

    if browser_data:
        total_cookies = browser_data.get("total_cookies", 0)
        nel_total = browser_data.get("reporting_nel", {}).get("total", 0)
        ts_total = browser_data.get("transport_security", {}).get("total", 0)
        summary_data.append(["Browser cookies extracted", str(total_cookies)])
        summary_data.append(["NEL records found", str(nel_total)])
        summary_data.append(["TransportSecurity domains", str(ts_total)])

    table = Table(summary_data, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

def _build_evidence_collection(story, styles, manifest_data: dict, case_id: str = None, investigator: str = None):
    """
    Documents the evidence source, acquisition method, and integrity hash.
    """
    story.append(Paragraph("Evidence Collection", styles['Heading1']))
    story.append(Spacer(1, 8))

    if case_id or investigator:
        case_lines = []
        if case_id:
            case_lines.append(f"<b>Case ID:</b> {case_id}")
        if investigator:
            case_lines.append(f"<b>Investigator:</b> {investigator}")
        for line in case_lines:
            story.append(Paragraph(line, styles['Normal']))
        story.append(Spacer(1, 10))

    rows = [["Field", "Value"], ["Evidence Source", manifest_data.get("directory", "unavailable")],
            ["Acquisition Method", "Direct logical file analysis (no imaging performed)"],
            ["Files in Manifest", str(manifest_data.get("files_included", 0))],
            ["Manifest Hash (SHA-256)", manifest_data.get("manifest_hash", "unavailable")],
            ["Manifest Errors", str(manifest_data.get("total_errors", 0))]]

    table = Table(rows, colWidths=[160, 310])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))

    note = manifest_data.get("note", "")
    if note:
        story.append(Paragraph(f"<i>{note}</i>", styles['Normal']))
    story.append(Spacer(1, 20))


def _build_file_details(story, styles, combined_data: dict, top_n: int = 10):
    story.append(Paragraph(f"File Metadata — Top {top_n} Files", styles['Heading1']))
    story.append(Spacer(1, 8))

    files = combined_data.get("files", [])[:top_n]

    if not files:
        story.append(Paragraph("No files to display.", styles['Normal']))
        story.append(Spacer(1, 20))
        return

    for f in files:
        name = f.get("name", "unknown")
        story.append(Paragraph(f"<b>{name}</b>", styles['Heading3']))

        rows = [["Field", "Value"]]
        # Pick most relevant fields — avoid dumping everything
        relevant_keys = [
            "path", "size_human", "time_modified", "time_created" if "time_created" in f else "time_ctime",
            "ctime_meaning", "format", "author", "creator_tool",
            "gps_latitude", "gps_longitude", "camera_model",
        ]
        for key in relevant_keys:
            if key in f and f[key] not in (None, "unavailable", ""):
                rows.append([key, str(f[key])[:80]])

        if len(rows) > 1:
            table = Table(rows, colWidths=[150, 320])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(table)
        story.append(Spacer(1, 10))

    remaining = combined_data.get("total_files", 0) - len(files)
    if remaining > 0:
        story.append(Paragraph(
            f"<i>{remaining} additional files scanned — details omitted, see summary above.</i>",
            styles['Normal']
        ))
    story.append(Spacer(1, 20))


def _build_browser_section(story, styles, browser_data: dict, top_n: int = 10):
    if not browser_data:
        return

    story.append(PageBreak())
    story.append(Paragraph("Browser Artifacts", styles['Heading1']))
    story.append(Spacer(1, 8))

    # Cookies
    story.append(Paragraph("Cookies", styles['Heading2']))
    for extraction in browser_data.get("cookies", []):
        browser_type = extraction.get("browser_type", "unknown")
        total = extraction.get("total", 0)
        story.append(Paragraph(f"<b>{browser_type}</b> — {total} cookies found", styles['Normal']))

        cookies = extraction.get("cookies", [])[:top_n]
        if cookies:
            rows = [["Domain", "Name", "Created", "Secure"]]
            for c in cookies:
                rows.append([
                    c.get("domain", "")[:30],
                    c.get("name", "")[:20],
                    c.get("created", "")[:20],
                    "Yes" if c.get("secure") else "No",
                ])
            table = Table(rows, colWidths=[150, 100, 130, 60])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#16a085")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(table)
        story.append(Spacer(1, 12))

    # NEL records
    nel = browser_data.get("reporting_nel", {})
    if nel.get("total", 0) > 0:
        story.append(Paragraph("Network Error Logging (NEL) Records", styles['Heading2']))
        story.append(Paragraph(
            f"Total: {nel['total']} — survives cookie/history clearing", styles['Normal']
        ))
        rows = [["Origin", "Last Accessed"]]
        for r in nel.get("records", [])[:top_n]:
            rows.append([r.get("origin", "")[:40], r.get("last_accessed", r.get("expires", ""))[:25]])
        table = Table(rows, colWidths=[280, 160])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8e44ad")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))


def _build_limitations(story, styles):
    story.append(PageBreak())
    story.append(Paragraph("Known Limitations", styles['Heading1']))
    story.append(Spacer(1, 8))

    limitations = [
        "Cookie values require DPAPI decryption — only works on same machine/session that created them.",
        "Chrome 127+ uses App-Bound Encryption — may block decryption even on same machine.",
        "TransportSecurity domain names are HMAC-hashed by some browsers (e.g. Brave) — not reversible without browser's secret key.",
        "NEL records only exist if the visited site explicitly sent NEL/Report-To headers — absence doesn't prove no visit.",
        "Browser internal file structures are undocumented and version-dependent — parsers may need updates for newer browser versions.",
    ]
    for item in limitations:
        story.append(Paragraph(f"• {item}", styles['Normal']))
        story.append(Spacer(1, 4))


def generate_pdf_report(
    combined_data: dict,
    output_path: str,
    browser_data: dict = None,
    manifest_data: dict = None,
    case_id: str = None,
    investigator: str = None,
    top_n: int = 10,
    scan_duration: float = None,
) -> str:
    """
    Generate a PDF forensic report.
    Returns:
        Path to generated PDF
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    scanned_path = combined_data.get("scanned_directory", "unknown")

    _build_header(story, styles, scanned_path, scan_duration)
    if manifest_data:
        _build_evidence_collection(story, styles, manifest_data, case_id, investigator)

    _build_summary(story, styles, combined_data, browser_data)
    _build_file_details(story, styles, combined_data, top_n)
    _build_browser_section(story, styles, browser_data, top_n)
    _build_limitations(story, styles)

    doc.build(story)
    return str(output_path)