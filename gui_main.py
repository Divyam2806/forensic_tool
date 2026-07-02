import sys
from pathlib import Path

# Add extractor/ to Python's import search path
# This must happen BEFORE importing anything from gui/
extractor_path = Path(__file__).resolve().parent / "extractor"
sys.path.insert(0, str(extractor_path))

from gui.main_window import launch_app

if __name__ == "__main__":
    launch_app()