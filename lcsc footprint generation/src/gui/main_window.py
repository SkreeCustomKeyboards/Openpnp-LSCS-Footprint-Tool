"""Main application window for OpenPnP Footprint Manager.

This module contains the primary GUI window and orchestrates the overall workflow.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QProgressBar,
    QStatusBar, QGroupBox, QSplitter, QHeaderView, QTextEdit,
    QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt6.QtGui import QAction

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper.lcsc_client import LCSCClient, LCSCApiError
from scraper.footprint_parser import FootprintParser
from models.footprint import Package
from models.part import Part
from gui.footprint_widget import FootprintPreviewWidget
from openpnp.backup import BackupManager, BackupError
from datetime import datetime


class FootprintFetchWorker(QThread):
    """Worker thread for fetching footprints from LCSC.

    Waits for user confirmation (via proceed() call) before fetching next footprint.

    Signals:
        progress: Emitted with (current, total, status_message)
        footprint_fetched: Emitted with (footprint_name, Package, lcsc_id)
        error: Emitted with (footprint_name, error_message)
        finished: Emitted when all footprints processed
    """

    progress = pyqtSignal(int, int, str)
    footprint_fetched = pyqtSignal(str, object, str)  # name, Package, lcsc_id
    error = pyqtSignal(str, str)  # name, error_message
    finished = pyqtSignal()

    def __init__(self, footprint_groups: list, session_id: str):
        """Initialize worker.

        Args:
            footprint_groups: List of FootprintGroup objects to process
            session_id: Unique session ID for this import batch
        """
        super().__init__()
        self._groups = footprint_groups
        self._session_id = session_id
        self._client = None
        self._parser = None
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._can_proceed = False

    def proceed(self):
        """Signal that worker can proceed to next footprint.

        Called by GUI when user clicks Confirm or Skip.
        """
        self._mutex.lock()
        self._can_proceed = True
        self._wait_condition.wakeOne()
        self._mutex.unlock()

    def run(self):
        """Fetch footprints in background thread."""
        self._client = LCSCClient()
        self._parser = FootprintParser()

        total = len(self._groups)

        for i, group in enumerate(self._groups):
            if self.isInterruptionRequested():
                break

            footprint_name = group.footprint_name
            lcsc_id = group.lcsc_number

            self.progress.emit(i + 1, total, f"Fetching {footprint_name} ({lcsc_id})...")

            try:
                # Fetch component data from LCSC
                component = self._client.fetch_component(lcsc_id)

                # Parse footprint with metadata
                package = self._parser.parse(
                    component.footprint_data,
                    footprint_name,
                    lcsc_id=lcsc_id,
                    session_id=self._session_id
                )

                # Emit success
                self.footprint_fetched.emit(footprint_name, package, lcsc_id)

            except LCSCApiError as e:
                self.error.emit(footprint_name, f"API Error: {e}")
            except Exception as e:
                self.error.emit(footprint_name, f"Parse Error: {e}")

            # Wait for user to confirm/skip before proceeding to next
            self._mutex.lock()
            self._can_proceed = False
            while not self._can_proceed and not self.isInterruptionRequested():
                self._wait_condition.wait(self._mutex)
            self._mutex.unlock()

        # Cleanup
        if self._client and self._client._client:
            self._client._client.close()

        self.finished.emit()


class MainWindow(QMainWindow):
    """Main application window.
    
    Provides the primary interface for:
    - Loading BOM files
    - Viewing analysis results
    - Processing footprints with confirmation
    - Managing backups
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenPnP Footprint Manager")
        self.setMinimumSize(1000, 900)
        self.resize(1200, 950)  # Set initial size larger than minimum

        # State
        self._bom_path: Optional[Path] = None
        self._openpnp_config_path: Optional[Path] = None
        self._bom_entries: list = []  # List of BomEntry objects
        self._footprint_groups: list = []  # List of FootprintGroup objects
        self._nozzle_tips: list = []  # List of (id, name) tuples for nozzle tips
        self._packages_manager = None  # PackagesManager instance
        self._parts_manager = None  # PartsManager instance
        self._analysis_results = None  # Analysis results dict

        # Processing state
        self._processing_queue: list = []  # Footprint groups to process
        self._current_package: Optional[Package] = None  # Currently previewing
        self._current_footprint_name: Optional[str] = None
        self._current_lcsc_id: Optional[str] = None
        self._worker: Optional[FootprintFetchWorker] = None
        self._confirmed_packages: list = []  # List of (Package, footprint_name, lcsc_id, height, nozzle) tuples
        self._confirmed_packages_map: dict = {}  # Map (footprint_name, lcsc_id, value) -> Package for lookup
        self._current_session_id: Optional[str] = None  # Current import session ID
        self._footprints_fetched: int = 0  # Counter for fetched footprints
        self._selected_bom_row: Optional[int] = None  # Currently selected BOM row for editing

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._detect_openpnp_config()
    
    def _setup_ui(self):
        """Initialize the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Top section: File selection and config
        top_group = self._create_file_section()
        main_layout.addWidget(top_group)
        
        # Middle section: Splitter with BOM table and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # BOM Table
        bom_group = self._create_bom_section()
        splitter.addWidget(bom_group)
        
        # Preview/Status area
        preview_group = self._create_preview_section()
        splitter.addWidget(preview_group)
        
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        
        # Bottom section: Action buttons and progress
        bottom_layout = self._create_action_section()
        main_layout.addLayout(bottom_layout)
    
    def _create_file_section(self) -> QGroupBox:
        """Create the file selection section."""
        group = QGroupBox("Configuration")
        layout = QHBoxLayout(group)

        # OpenPnP config path
        layout.addWidget(QLabel("OpenPnP Config:"))
        self._config_label = QLabel("Not detected")
        self._config_label.setStyleSheet("color: red;")
        self._config_label.setMaximumWidth(250)
        layout.addWidget(self._config_label, 0)  # 0 stretch factor

        self._browse_config_btn = QPushButton("Browse...")
        self._browse_config_btn.clicked.connect(self._browse_openpnp_config)
        layout.addWidget(self._browse_config_btn, 0)  # 0 stretch factor

        layout.addSpacing(20)

        # BOM file
        layout.addWidget(QLabel("BOM File:"))
        self._bom_label = QLabel("No file loaded")
        self._bom_label.setMaximumWidth(250)
        layout.addWidget(self._bom_label, 0)  # 0 stretch factor

        self._load_bom_btn = QPushButton("Load BOM...")
        self._load_bom_btn.clicked.connect(self._load_bom)
        layout.addWidget(self._load_bom_btn)

        layout.addSpacing(20)

        # Backup management buttons
        self._create_backup_btn = QPushButton("Create Backup")
        self._create_backup_btn.clicked.connect(self._manual_create_backup)
        self._create_backup_btn.setEnabled(False)  # Disabled until config is loaded
        layout.addWidget(self._create_backup_btn, 0)

        self._open_backups_btn = QPushButton("Navigate to Backups")
        self._open_backups_btn.clicked.connect(self._open_backup_folder)
        self._open_backups_btn.setEnabled(False)  # Disabled until config is loaded
        layout.addWidget(self._open_backups_btn, 0)

        layout.addStretch()

        # Prevent the group from expanding vertically
        from PyQt6.QtWidgets import QSizePolicy
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        return group
    
    def _create_bom_section(self) -> QGroupBox:
        """Create the BOM display section."""
        group = QGroupBox("BOM Contents")
        layout = QVBoxLayout(group)
        
        self._bom_table = QTableWidget()
        self._bom_table.setColumnCount(8)
        self._bom_table.setHorizontalHeaderLabels([
            "Reference", "Value", "OpenPnP Part Name", "Footprint", "LCSC #", "Height (mm)", "Nozzle", "Status"
        ])
        header = self._bom_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._bom_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._bom_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Make table read-only
        self._bom_table.cellClicked.connect(self._on_bom_row_clicked)

        layout.addWidget(self._bom_table)
        
        # Summary labels
        summary_layout = QHBoxLayout()
        self._total_label = QLabel("Total: 0")
        self._new_parts_label = QLabel("New Parts: 0")
        self._new_footprints_label = QLabel("New Footprints: 0")
        self._skip_label = QLabel("Skip (no LCSC): 0")
        
        summary_layout.addWidget(self._total_label)
        summary_layout.addWidget(self._new_parts_label)
        summary_layout.addWidget(self._new_footprints_label)
        summary_layout.addWidget(self._skip_label)
        summary_layout.addStretch()
        
        layout.addLayout(summary_layout)
        
        return group
    
    def _create_preview_section(self) -> QGroupBox:
        """Create the footprint preview section."""
        group = QGroupBox("Footprint Preview")
        layout = QVBoxLayout(group)

        # Graphical footprint preview
        self._preview_widget = FootprintPreviewWidget()
        self._preview_widget.setMinimumHeight(300)
        self._preview_widget.pad_clicked.connect(self._on_pad_clicked)
        layout.addWidget(self._preview_widget)

        # Footprint details (now with scroll)
        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout(details_group)
        self._details_label = QLabel("No footprint selected")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_layout.addWidget(self._details_label)
        layout.addWidget(details_group)

        # Part parameters group
        params_group = QGroupBox("Part Parameters")
        params_layout = QVBoxLayout(params_group)

        # Height row
        height_row = QHBoxLayout()
        height_row.addWidget(QLabel("Height (mm):"))
        self._height_input = QLineEdit()
        self._height_input.setText("0.5")
        self._height_input.setMaximumWidth(80)
        self._height_input.setPlaceholderText("0.5")
        height_row.addWidget(self._height_input)

        self._lcsc_link_btn = QPushButton("Open LCSC Page")
        self._lcsc_link_btn.setEnabled(False)
        self._lcsc_link_btn.clicked.connect(self._open_lcsc_page)
        height_row.addWidget(self._lcsc_link_btn)
        height_row.addStretch()
        params_layout.addLayout(height_row)

        # Nozzle selection row
        nozzle_row = QHBoxLayout()
        nozzle_row.addWidget(QLabel("Nozzle Tip:"))

        self._nozzle_combo = QComboBox()
        self._nozzle_combo.setMaximumWidth(150)
        nozzle_row.addWidget(self._nozzle_combo)

        nozzle_label = QLabel("(Auto-selected based on package size)")
        nozzle_label.setStyleSheet("color: gray; font-style: italic;")
        nozzle_row.addWidget(nozzle_label)
        nozzle_row.addStretch()
        params_layout.addLayout(nozzle_row)

        layout.addWidget(params_group)

        # Confirm/Skip buttons (for processing)
        btn_layout = QHBoxLayout()
        self._confirm_btn = QPushButton("Confirm")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._confirm_footprint)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setEnabled(False)
        self._skip_btn.clicked.connect(self._skip_footprint)

        btn_layout.addWidget(self._confirm_btn)
        btn_layout.addWidget(self._skip_btn)
        layout.addLayout(btn_layout)

        # Edit section (for clicking BOM rows after processing)
        self._edit_group = QGroupBox("Edit Selected Part")
        edit_layout = QVBoxLayout(self._edit_group)

        # Edit height row
        edit_height_row = QHBoxLayout()
        edit_height_row.addWidget(QLabel("Height (mm):"))
        self._edit_height_input = QLineEdit()
        self._edit_height_input.setMaximumWidth(80)
        self._edit_height_input.setPlaceholderText("0.5")
        edit_height_row.addWidget(self._edit_height_input)
        edit_height_row.addStretch()
        edit_layout.addLayout(edit_height_row)

        # Edit nozzle row
        edit_nozzle_row = QHBoxLayout()
        edit_nozzle_row.addWidget(QLabel("Nozzle Tip:"))
        self._edit_nozzle_combo = QComboBox()
        self._edit_nozzle_combo.setMaximumWidth(150)
        edit_nozzle_row.addWidget(self._edit_nozzle_combo)
        edit_nozzle_row.addStretch()
        edit_layout.addLayout(edit_nozzle_row)

        # Apply button
        apply_btn_layout = QHBoxLayout()
        self._apply_changes_btn = QPushButton("Apply Changes to Selected Part")
        self._apply_changes_btn.clicked.connect(self._apply_part_changes)
        apply_btn_layout.addWidget(self._apply_changes_btn)
        edit_layout.addLayout(apply_btn_layout)

        layout.addWidget(self._edit_group)

        # Initially hide edit section
        self._edit_group.setVisible(False)

        return group
    
    def _create_action_section(self) -> QHBoxLayout:
        """Create the action buttons and progress section."""
        layout = QHBoxLayout()
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)
        
        # Action buttons
        self._analyze_btn = QPushButton("Analyze")
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.clicked.connect(self._analyze_bom)
        layout.addWidget(self._analyze_btn)
        
        self._start_btn = QPushButton("Start Processing")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_processing)
        layout.addWidget(self._start_btn)

        self._write_btn = QPushButton("Write to OpenPnP")
        self._write_btn.setEnabled(False)
        self._write_btn.clicked.connect(self._write_to_openpnp)
        layout.addWidget(self._write_btn)

        self._restore_btn = QPushButton("Restore Backup")
        self._restore_btn.setEnabled(False)
        self._restore_btn.clicked.connect(self._restore_backup)
        layout.addWidget(self._restore_btn)

        return layout
    
    def _setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        load_bom_action = QAction("&Load BOM...", self)
        load_bom_action.setShortcut("Ctrl+O")
        load_bom_action.triggered.connect(self._load_bom)
        file_menu.addAction(load_bom_action)

        export_template_action = QAction("Export BOM &Template...", self)
        export_template_action.triggered.connect(self._export_bom_template)
        file_menu.addAction(export_template_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        self._dark_mode_action = QAction("&Dark Mode", self)
        self._dark_mode_action.setCheckable(True)
        self._dark_mode_action.setChecked(False)
        self._dark_mode_action.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(self._dark_mode_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Setup the status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready")
    
    def _detect_openpnp_config(self):
        """Auto-detect OpenPnP configuration directory."""
        from openpnp.config import find_openpnp_config
        
        config_path = find_openpnp_config()
        if config_path:
            self._set_openpnp_config(config_path)
        else:
            self._config_label.setText("Not found - please browse")
            self._config_label.setStyleSheet("color: orange;")
    
    def _set_openpnp_config(self, path: Path):
        """Set the OpenPnP configuration path.

        Args:
            path: Path to .openpnp2 directory
        """
        self._openpnp_config_path = path
        self._config_label.setText(str(path))
        self._config_label.setStyleSheet("color: green;")
        self._statusbar.showMessage(f"OpenPnP config: {path}")

        # Enable backup buttons
        self._create_backup_btn.setEnabled(True)
        self._open_backups_btn.setEnabled(True)

        # Check if backups exist and enable restore button
        self._check_and_enable_restore_button()

        # Load nozzle tips immediately when config is set
        self._load_nozzle_tips()
    
    def _browse_openpnp_config(self):
        """Browse for OpenPnP configuration directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select OpenPnP Configuration Directory",
            str(Path.home())
        )
        if path:
            config_path = Path(path)
            # Verify it looks like an OpenPnP config
            if (config_path / "packages.xml").exists():
                self._set_openpnp_config(config_path)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Directory",
                    "Selected directory doesn't appear to be an OpenPnP configuration.\n"
                    "Expected to find packages.xml in the directory."
                )
    
    def _load_bom(self):
        """Load a BOM file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load BOM File",
            str(Path.home()),
            "BOM Files (*.csv *.xlsx *.xls);;All Files (*)"
        )
        if path:
            self._bom_path = Path(path)
            self._bom_label.setText(self._bom_path.name)
            self._analyze_btn.setEnabled(True)
            self._statusbar.showMessage(f"Loaded BOM: {path}")
            
            # TODO: Parse BOM and populate table
            self._parse_and_display_bom()
    
    def _parse_and_display_bom(self):
        """Parse the loaded BOM and display in table."""
        if not self._bom_path:
            return

        try:
            from bom.parser import BomParser, BomParseError

            parser = BomParser()
            self._bom_entries = parser.parse(self._bom_path)
            self._footprint_groups = parser.group_by_footprint(self._bom_entries)

            # Populate the table
            self._bom_table.setRowCount(len(self._bom_entries))

            for row, entry in enumerate(self._bom_entries):
                # Reference
                self._bom_table.setItem(row, 0, QTableWidgetItem(entry.reference))
                # Value
                self._bom_table.setItem(row, 1, QTableWidgetItem(entry.value))
                # OpenPnP Part Name
                self._bom_table.setItem(row, 2, QTableWidgetItem(entry.part_id))
                # Footprint
                self._bom_table.setItem(row, 3, QTableWidgetItem(entry.footprint_name))
                # LCSC #
                lcsc_text = entry.lcsc_number if entry.lcsc_number else ""
                self._bom_table.setItem(row, 4, QTableWidgetItem(lcsc_text))
                # Height
                height_item = QTableWidgetItem("0.5")
                self._bom_table.setItem(row, 5, height_item)
                # Nozzle (initially empty, set during processing)
                nozzle_item = QTableWidgetItem("")
                self._bom_table.setItem(row, 6, nozzle_item)
                # Status
                status_text = "Has LCSC" if entry.has_lcsc else "No LCSC"
                self._bom_table.setItem(row, 7, QTableWidgetItem(status_text))

            # Update summary
            total = len(self._bom_entries)
            with_lcsc = sum(1 for e in self._bom_entries if e.has_lcsc)
            without_lcsc = total - with_lcsc
            unique_footprints = len(self._footprint_groups)

            self._total_label.setText(f"Total: {total}")
            self._new_parts_label.setText(f"With LCSC: {with_lcsc}")
            self._new_footprints_label.setText(f"Unique Footprints: {unique_footprints}")
            self._skip_label.setText(f"No LCSC: {without_lcsc}")

            self._statusbar.showMessage(
                f"Parsed {total} entries, {unique_footprints} unique footprints"
            )

        except BomParseError as e:
            QMessageBox.critical(
                self,
                "BOM Parse Error",
                f"Failed to parse BOM file:\n{e}"
            )
            self._statusbar.showMessage(f"Error parsing BOM: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Unexpected error parsing BOM:\n{e}"
            )
            self._statusbar.showMessage(f"Error: {e}")
    
    def _analyze_bom(self):
        """Analyze BOM against existing OpenPnP configuration."""
        if not self._bom_entries:
            QMessageBox.warning(
                self,
                "No BOM Loaded",
                "Please load a BOM file first."
            )
            return

        if not self._openpnp_config_path:
            QMessageBox.warning(
                self,
                "No OpenPnP Config",
                "Please select your OpenPnP configuration directory."
            )
            return

        # CRITICAL: Warn user that OpenPnP must be closed
        reply = QMessageBox.warning(
            self,
            "OpenPnP Must Be Closed",
            "IMPORTANT: OpenPnP must be closed before analyzing and importing footprints.\n\n"
            "If OpenPnP is open, it will overwrite any changes made by this tool when it closes, "
            "and all your work will be lost.\n\n"
            "Is OpenPnP currently closed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            QMessageBox.information(
                self,
                "Please Close OpenPnP",
                "Please close OpenPnP and click 'Analyze BOM' again when ready."
            )
            return

        try:
            from openpnp.packages_manager import PackagesManager, PackagesManagerError
            from openpnp.parts_manager import PartsManager, PartsManagerError

            # Load OpenPnP files
            self._statusbar.showMessage("Loading OpenPnP configuration...")

            packages_file = self._openpnp_config_path / "packages.xml"
            parts_file = self._openpnp_config_path / "parts.xml"

            self._packages_manager = PackagesManager(packages_file)
            self._packages_manager.load()

            self._parts_manager = PartsManager(parts_file)
            self._parts_manager.load()

            # Check for backups and enable restore button if any exist
            self._check_and_enable_restore_button()

            # Perform analysis
            self._statusbar.showMessage("Analyzing BOM...")
            results = self._perform_analysis()
            self._analysis_results = results

            # Display results
            self._display_analysis_results(results)

            # Enable next step
            if results["new_footprints_count"] > 0 or results["new_parts_count"] > 0:
                self._start_btn.setEnabled(True)

            self._statusbar.showMessage(
                f"Analysis complete: {results['new_footprints_count']} new footprints, "
                f"{results['new_parts_count']} new parts needed"
            )

        except (PackagesManagerError, PartsManagerError) as e:
            QMessageBox.critical(
                self,
                "OpenPnP File Error",
                f"Failed to load OpenPnP configuration:\n{e}"
            )
            self._statusbar.showMessage(f"Error loading OpenPnP files: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Analysis Error",
                f"Unexpected error during analysis:\n{e}"
            )
            self._statusbar.showMessage(f"Analysis error: {e}")
    
    def _perform_analysis(self) -> dict:
        """Perform cross-reference analysis between BOM and OpenPnP.

        Returns:
            Dict with analysis results
        """
        results = {
            "existing_footprints": [],
            "new_footprints": [],
            "existing_parts": [],
            "new_parts": [],
            "no_lcsc": [],
            "existing_footprints_count": 0,
            "new_footprints_count": 0,
            "existing_parts_count": 0,
            "new_parts_count": 0,
            "no_lcsc_count": 0
        }

        # Check footprints (only those with LCSC numbers)
        for group in self._footprint_groups:
            # Skip groups without LCSC numbers - we can't fetch these
            if not group.has_lcsc:
                continue

            if self._packages_manager.has_package(group.footprint_name):
                results["existing_footprints"].append(group.footprint_name)
            else:
                results["new_footprints"].append(group.footprint_name)

        # Check parts
        for entry in self._bom_entries:
            if not entry.has_lcsc:
                results["no_lcsc"].append(entry)
                continue

            part_id = entry.part_id
            if self._parts_manager.has_part(part_id):
                results["existing_parts"].append(entry)
            else:
                results["new_parts"].append(entry)

        # Update counts
        results["existing_footprints_count"] = len(results["existing_footprints"])
        results["new_footprints_count"] = len(results["new_footprints"])
        results["existing_parts_count"] = len(results["existing_parts"])
        results["new_parts_count"] = len(results["new_parts"])
        results["no_lcsc_count"] = len(results["no_lcsc"])

        return results

    def _display_analysis_results(self, results: dict):
        """Display analysis results in a dialog.

        Args:
            results: Analysis results dict
        """
        # Build message
        msg = "Analysis Results:\n\n"

        msg += f"📦 Footprints:\n"
        msg += f"  • Already exist: {results['existing_footprints_count']}\n"
        msg += f"  • Need to create: {results['new_footprints_count']}\n\n"

        msg += f"🔧 Parts:\n"
        msg += f"  • Already exist: {results['existing_parts_count']}\n"
        msg += f"  • Need to create: {results['new_parts_count']}\n"
        msg += f"  • No LCSC (skip): {results['no_lcsc_count']}\n\n"

        if results['new_footprints_count'] > 0:
            msg += f"New footprints needed:\n"
            for fp in results['new_footprints'][:10]:
                msg += f"  • {fp}\n"
            if len(results['new_footprints']) > 10:
                msg += f"  ... and {len(results['new_footprints']) - 10} more\n"
            msg += "\n"

        if results['new_footprints_count'] == 0 and results['new_parts_count'] == 0:
            msg += "✅ All footprints and parts already exist in OpenPnP!\n"
            msg += "No action needed."
        else:
            msg += "Click 'Start Processing' to fetch and add the new footprints."

        # Show dialog
        QMessageBox.information(
            self,
            "Analysis Complete",
            msg
        )

        # Update summary labels with color coding
        self._new_footprints_label.setText(
            f"New Footprints: {results['new_footprints_count']}"
        )
        self._new_parts_label.setText(
            f"New Parts: {results['new_parts_count']}"
        )

    def _start_processing(self):
        """Start processing the footprint queue."""
        if not self._analysis_results:
            QMessageBox.warning(
                self,
                "No Analysis",
                "Please run analysis first before processing."
            )
            return

        # Build processing queue from analysis results
        self._processing_queue = []
        for group in self._footprint_groups:
            if group.has_lcsc and group.footprint_name in self._analysis_results["new_footprints"]:
                self._processing_queue.append(group)

        if not self._processing_queue:
            QMessageBox.information(
                self,
                "Nothing to Process",
                "No new footprints need to be created."
            )
            return

        # Disable buttons and BOM table during processing
        self._start_btn.setEnabled(False)
        self._analyze_btn.setEnabled(False)
        self._bom_table.setEnabled(False)  # Prevent clicking during processing

        # Hide edit section during processing
        self._edit_group.setVisible(False)
        self._selected_bom_row = None

        # Reset preview
        self._preview_widget.set_footprint(None)
        self._details_label.setText("Starting footprint fetch...")
        self._confirmed_packages = []
        self._confirmed_packages_map = {}
        self._footprints_fetched = 0

        # Generate unique session ID for this import batch
        from datetime import datetime
        import uuid
        session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self._current_session_id = session_id

        # Create and start worker thread
        self._worker = FootprintFetchWorker(self._processing_queue, session_id)
        self._worker.progress.connect(self._on_fetch_progress)
        self._worker.footprint_fetched.connect(self._on_footprint_fetched)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

        self._statusbar.showMessage(f"Processing {len(self._processing_queue)} footprints... (Session: {session_id})")

    def _on_fetch_progress(self, current: int, total: int, message: str):
        """Handle fetch progress updates.

        Args:
            current: Current item number
            total: Total items
            message: Status message
        """
        self._progress_bar.setValue(int(current / total * 100))
        self._statusbar.showMessage(f"[{current}/{total}] {message}")

    def _on_footprint_fetched(self, footprint_name: str, package: Package, lcsc_id: str):
        """Handle successful footprint fetch.

        Args:
            footprint_name: Name of the footprint
            package: Parsed Package object
            lcsc_id: LCSC part number used
        """
        # Increment counter
        self._footprints_fetched += 1
        total = len(self._processing_queue)

        # Store current package for confirmation
        self._current_package = package
        self._current_footprint_name = footprint_name
        self._current_lcsc_id = lcsc_id

        # Display preview
        self._display_footprint_preview(package, footprint_name, lcsc_id)

        # Auto-select appropriate nozzle
        self._auto_select_nozzle(footprint_name)

        # Update status to show position
        self._statusbar.showMessage(
            f"Footprint {self._footprints_fetched}/{total}: {footprint_name} - "
            f"Click Confirm or Skip"
        )

        # Enable confirm/skip buttons and LCSC link
        self._confirm_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)
        self._lcsc_link_btn.setEnabled(True)

    def _on_fetch_error(self, footprint_name: str, error_message: str):
        """Handle fetch error.

        Args:
            footprint_name: Name of the footprint that failed
            error_message: Error description
        """
        # Clear preview and show error in details
        self._preview_widget.set_footprint(None)
        self._details_label.setText(
            f"ERROR fetching {footprint_name}\n\n"
            f"{error_message}\n\n"
            f"Click 'Skip' to continue."
        )

        # Enable skip button only
        self._confirm_btn.setEnabled(False)
        self._skip_btn.setEnabled(True)

    def _on_fetch_finished(self):
        """Handle worker thread completion."""
        self._progress_bar.setValue(100)
        self._statusbar.showMessage("Footprint fetching complete!")

        # Show summary
        confirmed_count = len(self._confirmed_packages)
        total_count = len(self._processing_queue)
        skipped_count = total_count - confirmed_count

        summary_msg = (
            f"Footprint Processing Complete\n\n"
            f"Total processed: {total_count}\n"
            f"Confirmed: {confirmed_count}\n"
            f"Skipped: {skipped_count}\n\n"
        )

        if confirmed_count > 0:
            summary_msg += f"Ready to write {confirmed_count} new footprints to OpenPnP."

            reply = QMessageBox.question(
                self,
                "Write to OpenPnP?",
                summary_msg + "\n\nDo you want to write these footprints to OpenPnP?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._write_to_openpnp()
        else:
            summary_msg += "No footprints confirmed for addition."
            QMessageBox.information(
                self,
                "Processing Complete",
                summary_msg
            )

        # Re-enable buttons and BOM table
        self._start_btn.setEnabled(True)
        self._analyze_btn.setEnabled(True)
        self._confirm_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._bom_table.setEnabled(True)  # Re-enable clicking after processing

        # Enable Write button if there are confirmed packages
        if confirmed_count > 0:
            self._write_btn.setEnabled(True)

        # Reset preview
        self._preview_widget.set_footprint(None)
        self._details_label.setText("Processing complete.\n\nLoad a new BOM or re-analyze to continue.")
        self._details_label.setText("No footprint selected")

    def _get_height_for_entry(self, entry) -> float:
        """Get the height value from BOM table for a specific entry.

        Args:
            entry: BomEntry to get height for

        Returns:
            Height in mm (float)
        """
        # Find the row in the BOM table that matches this entry
        for row in range(self._bom_table.rowCount()):
            # Check if reference matches (column 0)
            ref_item = self._bom_table.item(row, 0)
            if ref_item and ref_item.text() == entry.reference:
                # Get height from column 5
                height_item = self._bom_table.item(row, 5)
                if height_item:
                    try:
                        return float(height_item.text())
                    except ValueError:
                        return 0.5  # Default if invalid
        return 0.5  # Default if not found

    def _get_nozzle_for_footprint(self, footprint_name: str, lcsc_id: str) -> Optional[str]:
        """Get the nozzle tip ID from BOM table for a specific footprint/LCSC combo.

        Args:
            footprint_name: Footprint name to look for
            lcsc_id: LCSC ID to match

        Returns:
            Nozzle tip ID (str) or None if not found
        """
        # Find any row in the BOM table that matches this footprint and LCSC
        for row in range(self._bom_table.rowCount()):
            # Get the entry for this row
            if row < len(self._bom_entries):
                entry = self._bom_entries[row]
                if entry.base_footprint == footprint_name and entry.lcsc_number == lcsc_id:
                    # Get nozzle from column 6
                    nozzle_item = self._bom_table.item(row, 6)
                    if nozzle_item and nozzle_item.text():
                        # Find the nozzle tip ID from the name
                        nozzle_name = nozzle_item.text()
                        for tip_id, tip_name in self._nozzle_tips:
                            if tip_name == nozzle_name:
                                return tip_id
        return None

    def _write_to_openpnp(self):
        """Write confirmed packages and parts to OpenPnP files with backup."""
        try:
            self._statusbar.showMessage("Creating backup...")

            # Create backup
            backup_dir = self._openpnp_config_path / "footprint_manager_backups"
            backup_manager = BackupManager(backup_dir, self._openpnp_config_path)
            backup = backup_manager.create_backup(
                description=f"Before adding {len(self._confirmed_packages)} footprints from session {self._current_session_id}"
            )

            self._statusbar.showMessage(f"Backup created: {backup.timestamp}")

            # Track what we're adding
            packages_added = []
            parts_added = []

            # Add confirmed packages to packages.xml
            self._statusbar.showMessage("Writing packages...")
            for package, footprint_name, lcsc_id, height, nozzle_tip_id in self._confirmed_packages:
                # Get the current nozzle from BOM table (in case user changed it after confirming)
                current_nozzle_id = self._get_nozzle_for_footprint(footprint_name, lcsc_id)
                if current_nozzle_id is None:
                    current_nozzle_id = nozzle_tip_id  # Fall back to originally confirmed nozzle

                # Replace old nozzle tip with new one if user changed it
                if current_nozzle_id != nozzle_tip_id:
                    # User changed the nozzle - remove old one and add new one
                    if nozzle_tip_id in package.compatible_nozzle_tip_ids:
                        package.compatible_nozzle_tip_ids.remove(nozzle_tip_id)
                    if current_nozzle_id not in package.compatible_nozzle_tip_ids:
                        package.compatible_nozzle_tip_ids.append(current_nozzle_id)
                else:
                    # No change - just ensure the nozzle is in the list
                    if current_nozzle_id and current_nozzle_id not in package.compatible_nozzle_tip_ids:
                        package.compatible_nozzle_tip_ids.append(current_nozzle_id)

                # Check if package already exists (skip if it does)
                if not self._packages_manager.has_package(package.id):
                    self._packages_manager.add_package(package)
                    packages_added.append(package.id)
                else:
                    # Package exists - update it to add the new nozzle tip
                    self._packages_manager.update_package(package)
                    packages_added.append(f"{package.id} (updated)")

            # Save packages.xml
            self._packages_manager.save()
            self._statusbar.showMessage(f"Wrote {len(packages_added)} packages to packages.xml")

            # Add parts to parts.xml (one part per BOM entry)
            self._statusbar.showMessage("Writing parts...")

            # Track which parts we've already written to avoid duplicates
            written_parts = set()

            for package, footprint_name, lcsc_id, height, nozzle_tip_id in self._confirmed_packages:
                # Find ALL BOM entries that use this footprint (regardless of LCSC number)
                # This ensures we create parts for all components sharing the same footprint:
                # - Resistors: R0402-10K, R0402-1K, R0402-100Ω, etc.
                # - Capacitors: C0402-100nF, C0402-1uF, C0402-10uF, etc.
                # - Inductors: L0603-10uH, L0603-22uH, etc.
                # Each gets its own part with unique LCSC number
                matching_entries = [e for e in self._bom_entries
                                    if e.base_footprint == footprint_name]

                for entry in matching_entries:
                    # Skip if we've already written this part
                    if entry.part_id in written_parts:
                        continue
                    written_parts.add(entry.part_id)
                    # Get height from BOM table for this specific entry
                    entry_height = self._get_height_for_entry(entry)

                    # Create Part object with entry's own LCSC number in name field
                    part = Part(
                        id=entry.part_id,
                        package_id=package.id,
                        height=entry_height,  # Use height from BOM table
                        speed=1.0,   # Default speed
                        name=entry.lcsc_number if entry.lcsc_number else None,  # Entry's LCSC part number
                        generator=package.generator,
                        import_date=package.import_date,
                        session_id=package.session_id,
                        lcsc_id=entry.lcsc_number  # Entry's LCSC part number
                    )

                    # Add or update part (allows re-writing with updated heights)
                    if self._parts_manager.has_part(part.id):
                        self._parts_manager.update_part(part)
                        parts_added.append(f"{part.id} (updated)")
                    else:
                        self._parts_manager.add_part(part)
                        parts_added.append(part.id)

            # Save parts.xml
            self._parts_manager.save()
            self._statusbar.showMessage(f"Wrote {len(parts_added)} parts to parts.xml")

            # Show success message
            success_msg = (
                f"✓ Successfully wrote to OpenPnP!\n\n"
                f"Packages added: {len(packages_added)}\n"
                f"Parts added: {len(parts_added)}\n\n"
                f"Backup created: {backup.timestamp}\n"
                f"Location: {backup.path}\n\n"
                f"⚠️ CRITICAL - Next Steps:\n"
                f"1. You can now OPEN OpenPnP to see the new parts\n"
                f"2. Test the parts to ensure they work correctly\n"
                f"3. If there are any issues, you can restore from the backup\n\n"
                f"Remember: OpenPnP must be CLOSED before running this tool again."
            )

            QMessageBox.information(
                self,
                "Write Complete",
                success_msg
            )

            self._statusbar.showMessage("OpenPnP files updated successfully")

            # Enable restore button now that we have a backup
            self._check_and_enable_restore_button()

        except BackupError as e:
            QMessageBox.critical(
                self,
                "Backup Error",
                f"Failed to create backup:\n{e}\n\nNo changes were made."
            )
            self._statusbar.showMessage(f"Backup error: {e}")

        except Exception as e:
            # Try to restore backup if something went wrong
            error_msg = f"Failed to write to OpenPnP:\n{e}"

            if 'backup' in locals():
                try:
                    backup_manager.restore_backup(backup)
                    error_msg += "\n\nBackup has been restored."
                except:
                    error_msg += "\n\n⚠️ Failed to restore backup! Please check your OpenPnP files."

            QMessageBox.critical(
                self,
                "Write Error",
                error_msg
            )
            self._statusbar.showMessage(f"Write error: {e}")

    def _display_footprint_preview(self, package: Package, footprint_name: str, lcsc_id: str):
        """Display footprint preview graphically.

        Args:
            package: Package object to preview
            footprint_name: Name of the footprint
            lcsc_id: LCSC part number
        """
        footprint = package.footprint

        # Display in graphical widget
        self._preview_widget.set_footprint(footprint)

        # Update details
        details = (
            f"<b>Footprint:</b> {footprint_name}<br>"
            f"<b>LCSC:</b> {lcsc_id}<br>"
            f"<b>Package ID:</b> {package.id}<br>"
            f"<b>Body:</b> {footprint.body_width:.2f} x {footprint.body_height:.2f} mm<br>"
            f"<b>Pads:</b> {len(footprint.pads)}<br>"
            f"<b>Description:</b> {package.description or 'N/A'}<br><br>"
            f"<i>Click on a pad to see its details</i>"
        )
        self._details_label.setText(details)

    def _on_pad_clicked(self, pad):
        """Handle pad click event.

        Args:
            pad: Pad object that was clicked
        """
        # Display pad details
        details = (
            f"<b>Selected Pad: {pad.name}</b><br><br>"
            f"<b>Position:</b><br>"
            f"  X: {pad.x:.3f} mm<br>"
            f"  Y: {pad.y:.3f} mm<br><br>"
            f"<b>Size:</b><br>"
            f"  Width: {pad.width:.3f} mm<br>"
            f"  Height: {pad.height:.3f} mm<br><br>"
            f"<b>Rotation:</b> {pad.rotation:.1f}°<br><br>"
            f"<i>Click another pad or outside to deselect</i>"
        )
        self._details_label.setText(details)

    def _on_bom_row_clicked(self, row: int, column: int):
        """Handle BOM table row click to preview footprint.

        Args:
            row: Row index that was clicked
            column: Column index that was clicked
        """
        # Only show preview if we have confirmed packages
        if not self._confirmed_packages_map:
            self._statusbar.showMessage("No footprints confirmed yet. Process footprints first.")
            return

        # Get the BOM entry for this row
        if row >= len(self._bom_entries):
            return

        entry = self._bom_entries[row]

        # Look up the package in our confirmed map
        # Try specific lookup first (footprint, lcsc, value) for exact match
        key = (entry.base_footprint, entry.lcsc_number, entry.value)
        package = self._confirmed_packages_map.get(key)

        # If not found, try to find ANY package with the same footprint
        # This handles cases where multiple parts share the same footprint
        # (e.g., R0402-1M, R0402-10K, R0402-100K all use R0402 footprint)
        if not package:
            for map_key, map_package in self._confirmed_packages_map.items():
                if map_key[0] == entry.base_footprint:  # map_key[0] is the footprint name
                    package = map_package
                    break

        if not package:
            self._statusbar.showMessage(
                f"Footprint {entry.base_footprint} not yet processed or was skipped"
            )
            self._preview_widget.set_footprint(None)
            self._details_label.setText(
                f"<b>Part:</b> {entry.part_id}<br>"
                f"<b>Footprint:</b> {entry.base_footprint}<br>"
                f"<b>LCSC:</b> {entry.lcsc_number or 'N/A'}<br><br>"
                f"<i>This footprint has not been confirmed yet.</i>"
            )
            return

        # Display the footprint preview
        footprint = package.footprint
        self._preview_widget.set_footprint(footprint)

        # Update details
        details = (
            f"<b>Part:</b> {entry.part_id}<br>"
            f"<b>Reference:</b> {entry.reference}<br>"
            f"<b>Value:</b> {entry.value}<br>"
            f"<b>Footprint:</b> {entry.base_footprint}<br>"
            f"<b>LCSC:</b> {entry.lcsc_number or 'N/A'}<br>"
            f"<b>Package ID:</b> {package.id}<br>"
            f"<b>Body:</b> {footprint.body_width:.2f} x {footprint.body_height:.2f} mm<br>"
            f"<b>Pads:</b> {len(footprint.pads)}<br>"
            f"<b>Description:</b> {package.description or 'N/A'}<br><br>"
            f"<i>Click on a pad to see its details</i>"
        )
        self._details_label.setText(details)

        # Show edit section and populate with current values
        self._selected_bom_row = row
        self._edit_group.setVisible(True)

        # Get current height from BOM table
        height_item = self._bom_table.item(row, 5)
        if height_item:
            self._edit_height_input.setText(height_item.text())
        else:
            self._edit_height_input.setText("0.5")

        # Get current nozzle from BOM table and set it in edit combo
        nozzle_item = self._bom_table.item(row, 6)
        if nozzle_item and nozzle_item.text():
            # Find and select this nozzle in the combo
            nozzle_name = nozzle_item.text()
            for i in range(self._edit_nozzle_combo.count()):
                if self._edit_nozzle_combo.itemText(i) == nozzle_name:
                    self._edit_nozzle_combo.setCurrentIndex(i)
                    break
        else:
            # Auto-select nozzle based on footprint if not set
            self._auto_select_nozzle_for_edit(entry.base_footprint)

        self._statusbar.showMessage(f"Viewing footprint: {entry.base_footprint} - Use edit controls below to modify")

    def _confirm_footprint(self):
        """Confirm the current footprint."""
        if not self._current_package:
            return

        # Get height from input field
        try:
            height = float(self._height_input.text())
            if height <= 0:
                QMessageBox.warning(
                    self,
                    "Invalid Height",
                    "Height must be greater than 0."
                )
                return
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Height",
                "Please enter a valid numeric height value."
            )
            return

        # Get selected nozzle tip ID
        nozzle_tip_id = self._nozzle_combo.currentData()
        nozzle_tip_name = self._nozzle_combo.currentText()

        # Add to confirmed list with height and nozzle
        self._confirmed_packages.append((
            self._current_package,
            self._current_footprint_name,
            self._current_lcsc_id,
            height,
            nozzle_tip_id
        ))

        # Store in map AND update height/nozzle in BOM table for ALL entries that use this footprint
        # This handles cases where multiple parts share the same footprint (e.g., C0402-1uF, C0402-10uF, C0402-100nF)
        # All parts with the same footprint get the same height and nozzle
        for row, entry in enumerate(self._bom_entries):
            if entry.base_footprint == self._current_footprint_name:
                # Use (footprint, lcsc, value) as key to differentiate parts with same footprint
                key = (entry.base_footprint, entry.lcsc_number, entry.value)
                self._confirmed_packages_map[key] = self._current_package

                # Update height and nozzle in BOM table for ALL entries with this footprint
                height_item = QTableWidgetItem(str(height))
                self._bom_table.setItem(row, 5, height_item)

                # Update nozzle (show just the name)
                nozzle_name = self._nozzle_combo.currentText()
                nozzle_item = QTableWidgetItem(nozzle_name)
                self._bom_table.setItem(row, 6, nozzle_item)

        self._statusbar.showMessage(
            f"Confirmed {self._current_footprint_name} (height: {height}mm) "
            f"({len(self._confirmed_packages)}/{len(self._processing_queue)})"
        )

        # Clear current and disable buttons
        self._current_package = None
        self._current_footprint_name = None
        self._current_lcsc_id = None
        self._confirm_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._lcsc_link_btn.setEnabled(False)

        # Reset height to default
        self._height_input.setText("0.5")

        # Clear preview and show waiting message
        self._preview_widget.set_footprint(None)
        self._details_label.setText("Waiting for next footprint...")

        # Tell worker to proceed to next footprint
        if self._worker:
            self._worker.proceed()

    def _skip_footprint(self):
        """Skip the current footprint."""
        if self._current_footprint_name:
            self._statusbar.showMessage(f"Skipped {self._current_footprint_name}")
        else:
            self._statusbar.showMessage("Skipped")

        # Clear current and disable buttons
        self._current_package = None
        self._current_footprint_name = None
        self._current_lcsc_id = None
        self._confirm_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._lcsc_link_btn.setEnabled(False)

        # Reset height to default
        self._height_input.setText("0.5")

        # Clear preview and show waiting message
        self._preview_widget.set_footprint(None)
        self._details_label.setText("Waiting for next footprint...")

        # Tell worker to proceed to next footprint
        if self._worker:
            self._worker.proceed()

    def _open_lcsc_page(self):
        """Open the LCSC product page in the default browser."""
        if not self._current_lcsc_id:
            QMessageBox.warning(
                self,
                "No LCSC ID",
                "No LCSC part number available for this footprint."
            )
            return

        import webbrowser
        url = f"https://www.lcsc.com/product-detail/{self._current_lcsc_id}.html"
        webbrowser.open(url)
        self._statusbar.showMessage(f"Opened LCSC page: {self._current_lcsc_id}")

    def _load_nozzle_tips(self):
        """Load nozzle tips from OpenPnP machine.xml."""
        if not self._openpnp_config_path:
            return

        machine_file = self._openpnp_config_path / "machine.xml"
        if not machine_file.exists():
            return

        try:
            from lxml import etree
            tree = etree.parse(str(machine_file))
            root = tree.getroot()

            self._nozzle_tips = []
            nozzle_tip_elements = root.findall('.//nozzle-tip')

            for tip_elem in nozzle_tip_elements:
                tip_id = tip_elem.get('id', '')
                name = tip_elem.get('name', tip_id)
                if tip_id:
                    self._nozzle_tips.append((tip_id, name))

            # Populate combo boxes (show only name, store ID as data)
            self._nozzle_combo.clear()
            self._edit_nozzle_combo.clear()
            for tip_id, name in self._nozzle_tips:
                self._nozzle_combo.addItem(name, tip_id)
                self._edit_nozzle_combo.addItem(name, tip_id)

            self._statusbar.showMessage(f"Loaded {len(self._nozzle_tips)} nozzle tips")

        except Exception as e:
            self._statusbar.showMessage(f"Failed to load nozzle tips: {e}")

    def _auto_select_nozzle(self, footprint_name: str):
        """Auto-select appropriate nozzle based on package size.

        Strips C/R/L prefixes and matches to nozzle sizes.
        Implements fallback: CN##0 → CN##5 if CN##0 not available.

        Mapping based on common SMD package sizes (shifted one size smaller):
        - 01005, 0201, 0402: CN040 (0.40mm) - tiny to small parts
        - 0603, 0805: CN065 (0.65mm) - small parts
        - 1206, 1210: CN140 (1.40mm) - medium parts
        - 1812, 2512, SOT-23, SOT-223, SOD-123: CN220 (2.20mm)
        - SOIC, TSSOP, QFN, DFN: CN220 (2.20mm)
        - QFP, PLCC: CN400 (4.00mm)
        - Large connectors, shields: CN750 (7.50mm)
        """
        import re

        # Strip common component prefixes (C, R, L for capacitor, resistor, inductor)
        name_upper = footprint_name.upper()
        # Remove C/R/L prefix if followed by digits (C0402 → 0402, R0603 → 0603)
        name_clean = re.sub(r'^[CRL](?=\d)', '', name_upper)

        # Mapping: package patterns -> nozzle name (shifted one size smaller)
        nozzle_map = {
            'CN040': ['01005', '0201', '0402'],
            'CN065': ['0603', '0805'],
            'CN140': ['1206', '1210'],
            'CN220': ['1812', '2512', 'SOT-23', 'SOT-223', 'SOD-123',
                      'SOIC', 'TSSOP', 'QFN', 'DFN'],
            'CN400': ['QFP', 'PLCC', 'LQFP', 'TQFP'],
            'CN750': ['CONNECTOR', 'SHIELD', 'LARGE']
        }

        # Find matching nozzle
        selected_nozzle = 'CN065'  # Default to CN065 (common size)

        for nozzle_name, patterns in nozzle_map.items():
            for pattern in patterns:
                if pattern in name_clean:
                    selected_nozzle = nozzle_name
                    break
            if selected_nozzle != 'CN065' or nozzle_name == 'CN065':
                break

        # Get list of available nozzle names
        available_nozzles = [self._nozzle_combo.itemText(i) for i in range(self._nozzle_combo.count())]

        # Try to find exact match first
        found = False
        for i in range(self._nozzle_combo.count()):
            if selected_nozzle in self._nozzle_combo.itemText(i):
                self._nozzle_combo.setCurrentIndex(i)
                found = True
                break

        # If not found and nozzle ends with 0, try ##5 fallback
        if not found and selected_nozzle.endswith('0'):
            fallback_nozzle = selected_nozzle[:-1] + '5'  # CN040 → CN045
            for i in range(self._nozzle_combo.count()):
                if fallback_nozzle in self._nozzle_combo.itemText(i):
                    self._nozzle_combo.setCurrentIndex(i)
                    self._statusbar.showMessage(
                        f"Auto-selected {fallback_nozzle} (fallback for {selected_nozzle})"
                    )
                    break

    def _check_and_enable_restore_button(self):
        """Check if backups exist and enable restore button if so."""
        if not self._openpnp_config_path:
            self._restore_btn.setEnabled(False)
            return

        backup_dir = self._openpnp_config_path / "footprint_manager_backups"
        backup_manager = BackupManager(backup_dir, self._openpnp_config_path)
        backups = backup_manager.list_backups()

        if backups:
            self._restore_btn.setEnabled(True)
            self._statusbar.showMessage(f"Found {len(backups)} backup(s)")
        else:
            self._restore_btn.setEnabled(False)

    def _restore_backup(self):
        """Restore from backup."""
        if not self._openpnp_config_path:
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please load OpenPnP configuration first."
            )
            return

        # Get list of available backups
        backup_dir = self._openpnp_config_path / "footprint_manager_backups"
        backup_manager = BackupManager(backup_dir, self._openpnp_config_path)
        backups = backup_manager.list_backups()

        if not backups:
            QMessageBox.information(
                self,
                "No Backups",
                "No backups found."
            )
            return

        # Show list of backups to user
        from PyQt6.QtWidgets import QInputDialog
        backup_names = [f"{b.timestamp} - {b.manifest.description or 'No description'}" for b in backups]

        selected, ok = QInputDialog.getItem(
            self,
            "Select Backup",
            "Choose a backup to restore:",
            backup_names,
            0,
            False
        )

        if not ok:
            return

        # Get the selected backup
        selected_index = backup_names.index(selected)
        backup = backups[selected_index]

        # Confirm restoration
        reply = QMessageBox.question(
            self,
            "Restore Backup",
            f"Are you sure you want to restore backup from {backup.timestamp}?\n\n"
            f"Description: {backup.manifest.description or 'N/A'}\n\n"
            f"This will overwrite current OpenPnP configuration files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                backup_manager.restore_backup(backup)

                # Reload the managers
                self._packages_manager.load()
                self._parts_manager.load()

                QMessageBox.information(
                    self,
                    "Restore Complete",
                    f"Successfully restored backup from {backup.timestamp}\n\n"
                    f"Restart OpenPnP to see the restored configuration."
                )
                self._statusbar.showMessage(f"Backup restored: {backup.timestamp}")

            except BackupError as e:
                QMessageBox.critical(
                    self,
                    "Restore Failed",
                    f"Failed to restore backup:\n{e}"
                )
                self._statusbar.showMessage(f"Restore error: {e}")

    def _manual_create_backup(self):
        """Manually create a backup of current OpenPnP configuration."""
        if not self._openpnp_config_path:
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please load OpenPnP configuration first."
            )
            return

        try:
            backup_dir = self._openpnp_config_path / "footprint_manager_backups"
            backup_manager = BackupManager(backup_dir, self._openpnp_config_path)
            backup = backup_manager.create_backup(
                description=f"Manual backup created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            QMessageBox.information(
                self,
                "Backup Created",
                f"Backup successfully created:\n\n"
                f"Timestamp: {backup.timestamp}\n"
                f"Location: {backup_dir / backup.timestamp}"
            )
            self._statusbar.showMessage(f"Backup created: {backup.timestamp}")

        except BackupError as e:
            QMessageBox.critical(
                self,
                "Backup Failed",
                f"Failed to create backup:\n{e}"
            )
            self._statusbar.showMessage(f"Backup error: {e}")

    def _open_backup_folder(self):
        """Open the backup folder in system file explorer."""
        if not self._openpnp_config_path:
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please load OpenPnP configuration first."
            )
            return

        backup_dir = self._openpnp_config_path / "footprint_manager_backups"

        # Create backup directory if it doesn't exist
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

        # Open folder in system file explorer
        import sys
        import subprocess

        try:
            if sys.platform == 'win32':
                subprocess.run(['explorer', str(backup_dir)])
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(backup_dir)])
            else:  # linux
                subprocess.run(['xdg-open', str(backup_dir)])

            self._statusbar.showMessage(f"Opened backup folder: {backup_dir}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Cannot Open Folder",
                f"Could not open backup folder:\n{e}\n\n"
                f"Path: {backup_dir}"
            )

    def _export_bom_template(self):
        """Export a BOM template CSV file with correct column headers."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export BOM Template",
            "BOM_Template.csv",
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            import csv

            # Define the template headers in the exact order the program expects
            headers = [
                "Reference",          # Component reference (e.g., R1, C5)
                "Value",              # Component value (e.g., 10K, 100nF)
                "Footprint",          # Package/footprint name (e.g., C0402, SOT-23)
                "LCSC"                # LCSC part number (e.g., C25804)
            ]

            # Create sample rows to help users understand the format
            sample_data = [
                ["R1,R2,R3", "10K", "R0402", "C25804"],
                ["C1,C2", "100nF", "C0402", "C1525"],
                ["U1", "STM32F103C8T6", "LQFP-48_7x7x05P", "C8734"],
                ["", "", "", ""]  # Empty row for users to fill in
            ]

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(sample_data)

            QMessageBox.information(
                self,
                "Template Exported",
                f"BOM template saved successfully:\n\n{file_path}\n\n"
                f"The template includes:\n"
                f"- Correct column headers\n"
                f"- Sample data rows\n"
                f"- Reference format examples\n\n"
                f"You can open this file in Excel or any spreadsheet program."
            )
            self._statusbar.showMessage(f"Template exported: {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export template:\n{e}"
            )

    def _toggle_dark_mode(self, checked: bool):
        """Toggle between light and dark mode.

        Args:
            checked: True if dark mode enabled, False for light mode
        """
        from PyQt6.QtWidgets import QApplication

        if checked:
            # Dark mode stylesheet
            dark_stylesheet = """
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                }
                QGroupBox {
                    border: 1px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #f0f0f0;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    color: #f0f0f0;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px 15px;
                    color: #f0f0f0;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
                QPushButton:pressed {
                    background-color: #2a2a2a;
                }
                QPushButton:disabled {
                    background-color: #2b2b2b;
                    color: #666666;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #3d3d3d;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 3px;
                    color: #f0f0f0;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #f0f0f0;
                }
                QTableWidget {
                    background-color: #3d3d3d;
                    alternate-background-color: #353535;
                    border: 1px solid #555555;
                    color: #f0f0f0;
                    gridline-color: #555555;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #0078d4;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #3d3d3d;
                    color: #f0f0f0;
                    padding: 5px;
                    border: 1px solid #555555;
                }
                QLabel {
                    color: #f0f0f0;
                }
                QProgressBar {
                    border: 1px solid #555555;
                    border-radius: 3px;
                    text-align: center;
                    color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                }
                QStatusBar {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                }
                QMenuBar {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                }
                QMenuBar::item:selected {
                    background-color: #3d3d3d;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                    border: 1px solid #555555;
                }
                QMenu::item:selected {
                    background-color: #0078d4;
                }
                QTextBrowser {
                    background-color: #3d3d3d;
                    color: #f0f0f0;
                    border: 1px solid #555555;
                }
            """
            QApplication.instance().setStyleSheet(dark_stylesheet)
            self._statusbar.showMessage("Dark mode enabled")
        else:
            # Light mode - clear stylesheet to use default
            QApplication.instance().setStyleSheet("")
            self._statusbar.showMessage("Light mode enabled")

    def _auto_select_nozzle_for_edit(self, footprint_name: str):
        """Auto-select appropriate nozzle in edit combo based on footprint size.

        Args:
            footprint_name: Footprint name (e.g., "C0402", "SOT-23")
        """
        if not self._nozzle_tips or self._edit_nozzle_combo.count() == 0:
            return

        import re

        # Remove common prefixes (C, R, L) and convert to uppercase
        name_upper = footprint_name.upper()
        name_clean = re.sub(r'^[CRL](?=\d)', '', name_upper)

        # Nozzle mapping (adjusted per user request - one size smaller)
        nozzle_map = {
            'CN040': ['01005', '0201', '0402'],
            'CN065': ['0603', '0805'],
            'CN140': ['1206', '1210'],
            'CN220': ['1812', '2512', 'SOT-23', 'SOT-223', 'SOT-89'],
            'CN400': ['SOIC', 'SOP', 'TSSOP', 'QFP', 'LQFP'],
        }

        # Find matching nozzle
        selected_nozzle = None
        for nozzle_id, patterns in nozzle_map.items():
            for pattern in patterns:
                if pattern in name_clean:
                    selected_nozzle = nozzle_id
                    break
            if selected_nozzle:
                break

        # If no match, default to CN140
        if not selected_nozzle:
            selected_nozzle = 'CN140'

        # Try to select the nozzle
        found = False
        for i in range(self._edit_nozzle_combo.count()):
            nozzle_id = self._edit_nozzle_combo.itemData(i)
            if nozzle_id and nozzle_id.startswith(selected_nozzle):
                self._edit_nozzle_combo.setCurrentIndex(i)
                found = True
                break

        # If nozzle ends with '0', try fallback to '5' version (dual-head scheme)
        if not found and selected_nozzle.endswith('0'):
            fallback_nozzle = selected_nozzle[:-1] + '5'
            for i in range(self._edit_nozzle_combo.count()):
                nozzle_id = self._edit_nozzle_combo.itemData(i)
                if nozzle_id and nozzle_id.startswith(fallback_nozzle):
                    self._edit_nozzle_combo.setCurrentIndex(i)
                    break

    def _apply_part_changes(self):
        """Apply changes from edit controls to the selected BOM row."""
        if self._selected_bom_row is None:
            return

        # Validate height
        try:
            height = float(self._edit_height_input.text())
            if height <= 0:
                QMessageBox.warning(
                    self,
                    "Invalid Height",
                    "Height must be greater than 0."
                )
                return
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Height",
                "Please enter a valid numeric height value."
            )
            return

        # Get selected nozzle
        nozzle_id = self._edit_nozzle_combo.currentData()
        nozzle_name = self._edit_nozzle_combo.currentText()

        # Update the BOM table height and nozzle columns
        height_item = QTableWidgetItem(str(height))
        self._bom_table.setItem(self._selected_bom_row, 5, height_item)

        nozzle_item = QTableWidgetItem(nozzle_name)
        self._bom_table.setItem(self._selected_bom_row, 6, nozzle_item)

        # Update the confirmed packages list with new nozzle tip
        # Find the package that matches this entry's footprint and LCSC
        entry = self._bom_entries[self._selected_bom_row]
        for i, (package, footprint_name, lcsc_id, old_height, old_nozzle_id) in enumerate(self._confirmed_packages):
            if footprint_name == entry.base_footprint and lcsc_id == entry.lcsc_number:
                # Update the Package object's nozzle list directly
                # Remove old nozzle and add new nozzle
                if old_nozzle_id in package.compatible_nozzle_tip_ids:
                    package.compatible_nozzle_tip_ids.remove(old_nozzle_id)
                if nozzle_id not in package.compatible_nozzle_tip_ids:
                    package.compatible_nozzle_tip_ids.append(nozzle_id)

                # Replace the tuple with updated nozzle_tip_id
                self._confirmed_packages[i] = (package, footprint_name, lcsc_id, old_height, nozzle_id)
                break

        # Show confirmation
        self._statusbar.showMessage(
            f"Updated {entry.part_id}: Height={height}mm, Nozzle={nozzle_name}"
        )

        QMessageBox.information(
            self,
            "Changes Applied",
            f"Updated part: {entry.part_id}\n"
            f"Height: {height} mm\n"
            f"Nozzle: {nozzle_name}\n\n"
            f"Click 'Write to OpenPnP' to save changes."
        )

    def _show_about(self):
        """Show about dialog with clickable links."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("About OpenPnP Footprint Manager")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # Use QTextBrowser to support HTML with clickable links
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)  # Enable clicking links to open in browser
        text_browser.setHtml(
            "<html><body style='font-family: Arial, sans-serif;'>"
            "<h2 style='text-align: center;'>OpenPnP Footprint Manager</h2>"
            "<p style='text-align: center;'><b>Version 0.2.0</b></p>"
            "<p style='text-align: center;'>Import LCSC/EasyEDA footprints into OpenPnP.</p>"
            "<hr>"
            "<p><b>Created by:</b> Skree LLC - Marshall Somerville<br>"
            "<b>With:</b> Claude Code</p>"
            "<p><b>GitHub Repository:</b><br>"
            "<a href='https://github.com/SkreeCustomKeyboards/Openpnp-LSCS-Footprint-Tool'>"
            "https://github.com/SkreeCustomKeyboards/Openpnp-LSCS-Footprint-Tool</a></p>"
            "<hr>"
            "<p><b>Legal Notice:</b></p>"
            "<p style='font-size: 90%;'>All footprint data is retrieved from LCSC/EasyEDA and remains the "
            "exclusive property of LCSC and its respective rights holders. "
            "This tool is provided as-is for use with OpenPnP and does not claim "
            "ownership of any footprint data. Use at your own risk.</p>"
            "<p><b>For OpenPnP information:</b><br>"
            "<a href='https://github.com/openpnp/openpnp'>https://github.com/openpnp/openpnp</a></p>"
            "</body></html>"
        )
        layout.addWidget(text_browser)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()
