# Changelog

All notable changes to OpenPnP Footprint Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-16

### Fixed
- **CRITICAL: Y-axis coordinate inversion** - Fixed footprint orientation bug where pads were mirrored vertically
  - EasyEDA uses Y-axis increasing upward, OpenPnP uses Y-axis increasing downward
  - This caused pin 1 and other pads to appear in incorrect positions
  - Now correctly inverts Y-coordinates during conversion (src/scraper/footprint_parser.py:308)
  - Tested and verified with C730243 (QFN-16 package)
- **Restore Backup button availability** - Now enabled immediately on startup if backups exist
  - Previously required loading a BOM first
  - Critical for users needing to restore after discovering the Y-axis bug
- **Nozzle tip replacement** - Fixed regression where changing nozzles after processing left both old and new nozzles active
  - Now properly removes old nozzle and adds new nozzle when applying changes
  - Package object's nozzle list is updated directly in _apply_part_changes
- **OpenPnP closure warnings** - Added critical warnings about keeping OpenPnP closed
  - Warning before analyzing BOM - confirms OpenPnP is closed
  - Updated completion message to clarify OpenPnP can be opened after writing
  - Prevents data loss from OpenPnP overwriting tool changes

### Changed
- **Pad roundness handling** - Now respects pad shape from EasyEDA data
  - Round/circular pads: roundness=100
  - Oval pads: roundness=50
  - Rectangular pads: roundness=0
  - Ensures proper pad rendering in OpenPnP

### Added
- Dark mode support with comprehensive theme styling
  - Toggle in View menu
  - Professional dark theme for all UI elements
- BOM template export feature
  - File → Export BOM Template creates a sample CSV
  - Includes correct column headers and example data
  - Helps users structure their BOM files correctly
- Backup management buttons in Configuration section
  - "Create Backup" - Manually create backups before making changes
  - "Navigate to Backups" - Opens backup folder in file explorer
- Enhanced About dialog
  - Clickable GitHub repository link
  - Clickable OpenPnP link
  - Selectable text for easy copying
  - Credits and legal disclaimer

## [0.1.0] - 2025-01-15

### Added
- Initial release
- BOM file parsing (CSV and Excel)
- LCSC/EasyEDA footprint fetching
- Visual footprint preview
- Per-part height and nozzle tip configuration
- Automatic backup system with restore capability
- Smart handling of shared footprints
- OpenPnP parts.xml and packages.xml generation
- Windows GUI application with PyQt6

### Features
- Auto-detect OpenPnP configuration directory
- Support for parts with and without LCSC numbers
- Real-time footprint preview with pad visualization
- Batch processing with user confirmation
- Session-based tracking for bulk operations
- Metadata tracking in XML comments

[0.2.0]: https://github.com/SkreeCustomKeyboards/Openpnp-LSCS-Footprint-Tool/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SkreeCustomKeyboards/Openpnp-LSCS-Footprint-Tool/releases/tag/v0.1.0
