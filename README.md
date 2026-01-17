# OpenPnP Footprint Manager

A tool that automatically imports component footprints from LCSC into OpenPnP.

## What It Does

This tool reads your BOM file, fetches footprint data from LCSC, and adds the parts and footprints to your OpenPnP configuration. It eliminates the need to manually create footprints for each component.

## CRITICAL WARNING

OpenPnP MUST be completely closed before running this tool. If OpenPnP is open, it will overwrite all changes when it closes and your work will be lost.

## Requirements

- Python 3.10 or higher
- OpenPnP installed
- BOM file with LCSC part numbers

## Installation

### Portable Version (Recommended)

1. Download and extract the ZIP file
2. Double-click `OpenPnP_Footprint_Manager.bat`
3. The tool will automatically install dependencies on first run

### Standalone Version (Windows)

1. Download `OpenPnP_Footprint_Manager.exe`
2. Double-click to run (no Python installation needed)

### From Source

```bash
python main.py
```

Dependencies will be installed automatically on first run.

## Usage

1. Close OpenPnP completely
2. Launch the tool
3. Click "Load BOM" and select your BOM file
4. Click "Analyze" to see what needs to be imported
5. Click "Start Processing" to begin
6. Review each footprint preview and click "Confirm" or "Skip"
7. Click "Write to OpenPnP" when done
8. Open OpenPnP and verify the new parts work correctly

## BOM File Format

Your BOM needs these columns:

- **FOOTPRINT-NAME** - The package name (e.g., C0402, LQFP48)
- **LCSC** - The LCSC part number (e.g., C60490)
- Reference and Value columns are optional but helpful

Example BOM template:

```csv
Reference,Value,Footprint,LCSC
R1,10K,C0402,C60490
C1,100nF,C0402,C12345
U1,STM32,LQFP48,C8734
```

Use File → Export BOM Template to create a sample file.

## Features

- Automatic backup before making changes
- Visual footprint preview before importing
- Handles shared footprints (multiple parts using same package)
- Dark mode support
- Per-part height and nozzle tip configuration

## Troubleshooting

**Changes don't appear in OpenPnP**
- Make sure OpenPnP was closed before running the tool
- Try opening OpenPnP fresh after writing changes

**Footprint looks incorrect**
- Click "Skip" during processing and create it manually in OpenPnP
- Report issues on GitHub with the LCSC part number

**Need to undo changes**
- Use the "Restore Backup" button to revert to previous state
- Backups are created automatically before writing changes

## Links

- Report issues: https://github.com/SkreeCustomKeyboards/Openpnp-LSCS-Footprint-Tool/issues
- OpenPnP Documentation: https://github.com/openpnp/openpnp/wiki

## Credits

Created by Skree LLC - Marshall Somerville
Claude Code for all the heavy lifting with Python
Footprint data is retrieved from LCSC/EasyEDA and remains the property of LCSC and its respective rights holders.

## License

See LICENSE file for details.
