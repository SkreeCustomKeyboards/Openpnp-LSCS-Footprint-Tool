#!/usr/bin/env python3
"""
OpenPnP Footprint Manager

A GUI application for importing LCSC/EasyEDA footprints into OpenPnP.

Usage:
    python main.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    """Application entry point."""
    from PyQt6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    
    app = QApplication(sys.argv)
    app.setApplicationName("OpenPnP Footprint Manager")
    app.setOrganizationName("OpenPnP-Tools")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
