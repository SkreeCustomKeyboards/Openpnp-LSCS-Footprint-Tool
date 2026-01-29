# Changelog

All notable changes to OpenPnP Footprint Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - Unreleased

### Fixed
- **CSV parsing failures** - Fixed BOM parser incorrectly treating comma-separated CSV files as tab-separated
  - Parser was hardcoded to use tab separator for all CSV files
  - Now tries comma separator first (most common), then tab and semicolon
  - Added support for multiple encoding/separator combinations
- **UTF-16 encoding error** - Fixed "UTF-16 stream does not start with BOM" error
  - Changed encoding priority to try UTF-8 first before UTF-16
  - Standard CSV files now parse correctly
- **JLCPCB column name support** - Added "JLCPCB Part #" and variations to recognized LCSC column names
  - JLCPCB and LCSC use the same part numbering system
  - Now recognizes: "JLCPCB Part", "JLCPCB Part #", "JLCPCB", "JLCPCB#"

### Improved
- **Enhanced CSV format compatibility**
  - Added semicolon separator support (European CSV format)
  - Added cp1252 encoding support (Windows default)
  - Better handling of extra whitespace in column names
  - Skip empty rows automatically
  - Improved NA/null value handling
  - Validates that parsed files contain actual data
- **Better column name detection**
  - Added more column name variations: "Component", "Description", "Part Number", "PCB Footprint"
  - Case-insensitive matching with whitespace trimming
  - More flexible column header recognition
- **Error messages** - More descriptive messages when CSV parsing fails

## [0.2.0] - 2025-01-29

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
