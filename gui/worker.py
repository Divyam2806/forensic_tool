from PySide6.QtCore import QThread, Signal
from pathlib import Path
import json


SOLR_PATH = Path(__file__).parent.parent/ 'metadata-json'

class ScanWorker(QThread):
    """
    Runs combine_metadata() in a background thread.
    Emits 'finished' signal with results when done.
    Emits 'error' signal if something goes wrong.
    """
    finished = Signal(dict)
    error    = Signal(str)
    progress = Signal(str)   # status text updates

    def __init__(self, scan_path: str, max_files: int = 1000):
        super().__init__()
        self.scan_path = scan_path
        self.max_files = max_files

    def run(self):
        """
        QThread calls this automatically when .start() is called.
        Runs on background thread — must not touch GUI widgets directly,
        only emit signals.
        """
        try:
            self.progress.emit("Scanning file system and content metadata...")

            # Import here, not at module level — avoids circular import
            # issues since combine_metadata lives in extractor/main.py
            from main import combine_metadata, export_for_indexing

            result = combine_metadata(self.scan_path, max_files=self.max_files)

            # need to fix exporting issue
            export_for_indexing(result, output_folder=SOLR_PATH)

            if "error" in result:
                self.error.emit(result["error"])
                return

            self.progress.emit("Scan complete.")
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class BrowserWorker(QThread):
    """
    Runs extract_network_artifacts() in a background thread.
    Separate from ScanWorker since browser scanning targets
    a different folder (Network folder) than fs+file scanning.
    """
    finished = Signal(dict)
    error    = Signal(str)
    progress = Signal(str)

    def __init__(self, network_folder: str):
        super().__init__()
        self.network_folder = network_folder

    def run(self):
        try:
            self.progress.emit("Extracting browser artifacts...")

            from modules.browser_artifacts import extract_network_artifacts

            result = extract_network_artifacts(self.network_folder)

            if "error" in result:
                self.error.emit(result["error"])
                return

            self.progress.emit("Browser extraction complete.")
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class ReportWorker(QThread):
    """
    Runs generate_pdf_report() in a background thread.
    PDF generation with many files can take a few seconds,
    keeping it off the main thread avoids any UI hiccup.
    """
    finished = Signal(str)   # emits the saved PDF path
    error    = Signal(str)

    def __init__(self, combined_data: dict, output_path: str,
                 browser_data: dict = None, top_n: int = 10,
                 scan_duration: float = None):
        super().__init__()
        self.combined_data = combined_data
        self.output_path   = output_path
        self.browser_data  = browser_data
        self.top_n         = top_n
        self.scan_duration = scan_duration

    def run(self):
        try:
            from modules.report_generator import generate_pdf_report

            path = generate_pdf_report(
                combined_data=self.combined_data,
                output_path=self.output_path,
                browser_data=self.browser_data,
                top_n=self.top_n,
                scan_duration=self.scan_duration,
            )
            self.finished.emit(path)

        except Exception as e:
            self.error.emit(str(e))