import sys
import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit,
    QProgressBar, QMessageBox, QLineEdit
)

from gui.worker import ScanWorker, BrowserWorker, ReportWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forensic Evidence Extractor")
        self.setMinimumSize(700, 600)

        # State — holds results between steps
        self.scan_results    = None
        self.browser_results = None
        self.scan_duration   = None

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout  = QVBoxLayout()

        # ── Evidence folder selection ────────────────────────────────
        layout.addWidget(QLabel("<b>Step 1 — Select Evidence Folder</b>"))

        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("No folder selected...")
        self.folder_input.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._select_folder)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        self.scan_btn = QPushButton("Start Scan (FS + File Metadata)")
        self.scan_btn.clicked.connect(self._start_scan)
        self.scan_btn.setEnabled(False)
        layout.addWidget(self.scan_btn)

        # ── Browser artifacts ────────────────────────────────────────
        layout.addWidget(QLabel("<b>Step 2 — Browser Artifacts (Optional)</b>"))

        browser_row = QHBoxLayout()
        self.browser_input = QLineEdit()
        self.browser_input.setPlaceholderText("Select browser Network folder...")
        self.browser_input.setReadOnly(True)
        browser_browse_btn = QPushButton("Browse...")
        browser_browse_btn.clicked.connect(self._select_browser_folder)
        browser_row.addWidget(self.browser_input)
        browser_row.addWidget(browser_browse_btn)
        layout.addLayout(browser_row)

        self.browser_btn = QPushButton("Extract Browser Artifacts")
        self.browser_btn.clicked.connect(self._start_browser_scan)
        self.browser_btn.setEnabled(False)
        layout.addWidget(self.browser_btn)

        # ── Progress + status ────────────────────────────────────────
        layout.addWidget(QLabel("<b>Status</b>"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate spinner style
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setMaximumHeight(150)
        layout.addWidget(self.status_log)

        # ── Step 3 — Report ──────────────────────────────────────────
        layout.addWidget(QLabel("<b>Step 3 — Generate Report</b>"))
        self.report_btn = QPushButton("Generate PDF Report")
        self.report_btn.clicked.connect(self._generate_report)
        self.report_btn.setEnabled(False)
        layout.addWidget(self.report_btn)

        # ── Step 4 — Indexing ────────────────────────────────────────
        layout.addWidget(QLabel("<b>Step 4 — Indexing (Java/Solr)</b>"))
        self.index_btn = QPushButton("Run Indexing")
        self.index_btn.clicked.connect(self._run_indexing)
        self.index_btn.setEnabled(False)
        layout.addWidget(self.index_btn)

        central.setLayout(layout)
        self.setCentralWidget(central)

    # ── Step 1 handlers ──────────────────────────────────────────────
    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Evidence Folder")
        if folder:
            self.folder_input.setText(folder)
            self.scan_btn.setEnabled(True)

    def _start_scan(self):
        path = self.folder_input.text()
        if not path:
            return

        self._log(f"Starting scan: {path}")
        self.progress_bar.setVisible(True)
        self.scan_btn.setEnabled(False)

        self._scan_start_time = datetime.datetime.now()

        self.scan_worker = ScanWorker(path, max_files=1000)
        self.scan_worker.progress.connect(self._log)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    def _on_scan_finished(self, result: dict):
        self.scan_results  = result
        self.scan_duration = (
            datetime.datetime.now() - self._scan_start_time
        ).total_seconds()

        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.report_btn.setEnabled(True)
        self.index_btn.setEnabled(True)

        total = result.get("total_files", 0)
        self._log(f"Scan complete — {total} files processed in {self.scan_duration:.2f}s")

    def _on_scan_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self._log(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Scan Failed", error_msg)

    # ── Step 2 handlers ──────────────────────────────────────────────
    def _select_browser_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Browser Network Folder")
        if folder:
            self.browser_input.setText(folder)
            self.browser_btn.setEnabled(True)

    def _start_browser_scan(self):
        path = self.browser_input.text()
        if not path:
            return

        self._log(f"Extracting browser artifacts: {path}")
        self.progress_bar.setVisible(True)
        self.browser_btn.setEnabled(False)

        self.browser_worker = BrowserWorker(path)
        self.browser_worker.progress.connect(self._log)
        self.browser_worker.finished.connect(self._on_browser_finished)
        self.browser_worker.error.connect(self._on_browser_error)
        self.browser_worker.start()

    def _on_browser_finished(self, result: dict):
        self.browser_results = result
        self.progress_bar.setVisible(False)
        self.browser_btn.setEnabled(True)

        total_cookies = result.get("total_cookies", 0)
        self._log(f"Browser extraction complete — {total_cookies} cookies found")

    def _on_browser_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.browser_btn.setEnabled(True)
        self._log(f"ERROR: {error_msg}")
        QMessageBox.warning(self, "Browser Extraction Failed", error_msg)

    # ── Step 3 — Report ──────────────────────────────────────────────
    def _generate_report(self):
        if not self.scan_results:
            QMessageBox.warning(self, "No Data", "Run a scan first.")
            return

        timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(__file__).resolve().parent.parent /
                           "extractor" / "output" / f"forensic_report_{timestamp}.pdf")

        self._log("Generating PDF report...")
        self.progress_bar.setVisible(True)
        self.report_btn.setEnabled(False)

        self.report_worker = ReportWorker(
            combined_data=self.scan_results,
            output_path=output_path,
            browser_data=self.browser_results,
            top_n=10,
            scan_duration=self.scan_duration,
        )
        self.report_worker.finished.connect(self._on_report_finished)
        self.report_worker.error.connect(self._on_report_error)
        self.report_worker.start()

    def _on_report_finished(self, path: str):
        self.progress_bar.setVisible(False)
        self.report_btn.setEnabled(True)
        self._log(f"Report saved: {path}")
        QMessageBox.information(self, "Report Generated", f"Saved to:\n{path}")

    def _on_report_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.report_btn.setEnabled(True)
        self._log(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Report Generation Failed", error_msg)

    # ── Step 4 — Indexing ─────────────────────────────────────────────
    def _run_indexing(self):
        """
        Placeholder — actual subprocess call to Java indexer
        will be added once teammate provides standalone jar + entry points.
        """
        self._log("Indexing step — pending Java module updates from teammate.")
        QMessageBox.information(
            self, "Not Yet Available",
            "Indexing integration is pending updates to the Java module."
        )

    # ── Utility ────────────────────────────────────────────────────────
    def _log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_log.append(f"[{timestamp}] {message}")


def launch_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())