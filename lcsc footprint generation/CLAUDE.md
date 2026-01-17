# OpenPnP Footprint Manager - Claude Code Guidelines

## Project Overview

This project creates a GUI application that automates importing component footprints from LCSC/EasyEDA into OpenPnP's configuration files. It parses BOM files, identifies missing parts/footprints, scrapes footprint data from LCSC, and safely updates OpenPnP's XML configuration.

## Architecture

```
openpnp-footprint-manager/
├── CLAUDE.md                 # This file - coding guidelines
├── README.md                 # User documentation
├── requirements.txt          # Python dependencies
├── main.py                   # Application entry point
├── src/
│   ├── __init__.py
│   ├── gui/                  # PyQt6 GUI components
│   │   ├── __init__.py
│   │   ├── main_window.py    # Main application window
│   │   ├── bom_viewer.py     # BOM parsing and display
│   │   ├── footprint_preview.py  # Footprint visualization
│   │   └── part_list_widget.py   # Parts queue management
│   ├── openpnp/              # OpenPnP file handling
│   │   ├── __init__.py
│   │   ├── config.py         # OpenPnP config path detection
│   │   ├── backup.py         # Backup/restore management
│   │   ├── parts_manager.py  # parts.xml operations
│   │   └── packages_manager.py   # packages.xml operations
│   ├── scraper/              # LCSC/EasyEDA data fetching
│   │   ├── __init__.py
│   │   ├── lcsc_client.py    # LCSC API client
│   │   └── footprint_parser.py   # EasyEDA JSON to OpenPnP conversion
│   ├── bom/                  # BOM file processing
│   │   ├── __init__.py
│   │   └── parser.py         # BOM parsing (CSV, Excel)
│   └── models/               # Data models
│       ├── __init__.py
│       ├── footprint.py      # Footprint data structures
│       └── part.py           # Part data structures
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_bom_parser.py
│   ├── test_openpnp_manager.py
│   └── test_scraper.py
└── docs/
    └── PROJECT_OVERVIEW.md   # Detailed project documentation
```

## Technology Stack

- **Python 3.10+**
- **GUI**: PyQt6 (cross-platform, professional appearance)
- **HTTP Client**: httpx (async support, modern API)
- **XML Parsing**: lxml (robust XML handling with XPath)
- **BOM Parsing**: pandas (Excel/CSV handling), openpyxl
- **Web Scraping**: playwright (for JavaScript-rendered content if needed)
- **Testing**: pytest

## Critical Files Reference

### OpenPnP Configuration Files

Located at:
- Windows: `C:\Users\{username}\.openpnp2\`
- Linux: `/home/{username}/.openpnp2/`
- macOS: `/Users/{username}/.openpnp2/`

Key files:
- `parts.xml` - Part definitions with package references
- `packages.xml` - Package/footprint definitions with pads

### OpenPnP XML Structures

**packages.xml format:**
```xml
<openpnp-packages>
    <package version="1.1" id="R0402" description="Resistor R0402">
        <footprint units="Millimeters" body-width="1.0" body-height="0.5">
            <pad name="1" x="-0.5" y="0.0" width="0.5" height="0.6" rotation="0.0" roundness="0.0"/>
            <pad name="2" x="0.5" y="0.0" width="0.5" height="0.6" rotation="0.0" roundness="0.0"/>
        </footprint>
    </package>
</openpnp-packages>
```

**parts.xml format:**
```xml
<openpnp-parts>
    <part id="R_0402-10K" height-units="Millimeters" height="0.5" package-id="R0402" speed="1.0"/>
</openpnp-parts>
```

### LCSC/EasyEDA API Reference

The easyeda2kicad project provides working API patterns:
- GitHub: https://github.com/uPesy/easyeda2kicad.py
- API endpoint pattern: `https://easyeda.com/api/products/{lcsc_id}/svgs`
- Component data includes pad positions, sizes, and shapes

## Development Phases (Lockstep)

### Phase 1: Core Infrastructure
- [ ] Project setup, dependencies
- [ ] Basic PyQt6 window scaffold
- [ ] OpenPnP config path detection
- [ ] File existence validation

### Phase 2: BOM Processing
- [ ] CSV/Excel BOM parser
- [ ] Extract unique parts from FOOTPRINT-NAME column
- [ ] Extract LCSC part numbers from "supplier part" column
- [ ] Handle missing/empty LCSC numbers (skip)
- [ ] Display parsed BOM in GUI table

### Phase 3: OpenPnP File Reading
- [ ] Parse existing packages.xml
- [ ] Parse existing parts.xml
- [ ] Index existing footprints by ID
- [ ] Index existing parts by ID

### Phase 4: Cross-Reference Analysis
- [ ] Compare BOM parts against OpenPnP parts
- [ ] Identify parts needing creation
- [ ] Identify footprints needing creation
- [ ] Handle shared footprints (C0402, etc.)
- [ ] Generate work queue

### Phase 5: Backup System
- [ ] Create timestamped backups before changes
- [ ] Track backup location
- [ ] Implement restore capability
- [ ] User confirmation before backup deletion

### Phase 6: LCSC Scraping
- [ ] Implement LCSC API client
- [ ] Fetch EasyEDA footprint data by LCSC number
- [ ] Parse JSON pad data
- [ ] Handle API errors gracefully

### Phase 7: Footprint Conversion
- [ ] Convert EasyEDA pad format to OpenPnP format
- [ ] Handle different pad shapes (rect, round, oval)
- [ ] Calculate body dimensions from pad extents
- [ ] Validate converted footprints

### Phase 8: GUI Preview & Approval
- [ ] Render footprint preview in GUI
- [ ] Show pad positions visually
- [ ] Confirm/Skip buttons per footprint
- [ ] Progress indicator for queue

### Phase 9: OpenPnP File Writing
- [ ] Add new packages to packages.xml
- [ ] Add new parts to parts.xml
- [ ] Preserve existing entries
- [ ] Validate XML before saving

### Phase 10: Integration & Testing
- [ ] End-to-end workflow testing
- [ ] Error handling refinement
- [ ] User feedback on backup deletion
- [ ] Documentation

## Coding Standards

### Python Style
```python
# Use type hints throughout
def parse_bom(filepath: Path) -> list[BomEntry]:
    """Parse a BOM file and return list of entries.
    
    Args:
        filepath: Path to the BOM file (CSV or XLSX)
        
    Returns:
        List of BomEntry objects with part information
        
    Raises:
        BomParseError: If the file format is invalid
    """
    pass
```

### Error Handling
```python
# Define specific exceptions
class OpenPnPConfigError(Exception):
    """OpenPnP configuration file error."""
    pass

class LCSCApiError(Exception):
    """LCSC API communication error."""
    pass

# Use context managers for file operations
with backup_manager.create_backup() as backup:
    try:
        packages_manager.add_package(new_package)
        packages_manager.save()
    except Exception as e:
        backup.restore()
        raise
```

### GUI Patterns
```python
# Use signals/slots for thread-safe updates
class FootprintWorker(QThread):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)
    
    def run(self):
        try:
            result = self.fetch_footprint()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

### Data Models
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Pad:
    name: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    roundness: float = 0.0  # 0=rect, 100=circle

@dataclass
class Footprint:
    id: str
    description: Optional[str]
    body_width: float
    body_height: float
    pads: list[Pad]
    units: str = "Millimeters"
```

## Key Implementation Notes

### Shared Footprint Handling
Many components share the same footprint (e.g., all C0402 capacitors/resistors use the same package). The system must:

1. Extract the base footprint name from BOM (e.g., "C0402" from "C0402-100nF")
2. Check if that footprint already exists in packages.xml
3. Only create the footprint once, reuse for multiple parts
4. Track which footprint ID is used for each part

### User Confirmation Flow
```
1. Load BOM
2. Analyze → Show summary of what needs to be created
3. User clicks "Start"
4. For each item in queue:
   a. Fetch footprint from LCSC
   b. Display preview
   c. Wait for Confirm/Skip
   d. On Confirm: Write to XML
   e. On Skip: Mark as skipped, continue
5. Show completion summary
6. Ask user to verify changes in OpenPnP
7. User confirms changes work → Delete backup
8. User reports issues → Offer restore from backup
```

### Backup Strategy
```python
# Backup naming: packages.xml.backup.20240115_143022
# Keep backups until user explicitly confirms changes work
# Store backup manifest with original file hashes for verification
```

## Testing Approach

### Unit Tests
- BOM parser: various CSV/Excel formats
- XML parsing: malformed files, missing elements
- Footprint conversion: different pad configurations

### Integration Tests
- Full workflow with mock LCSC responses
- Backup/restore cycle
- GUI interactions with pytest-qt

### Test Data
Keep sample files in `tests/fixtures/`:
- `sample_bom.csv` - typical BOM file
- `sample_packages.xml` - OpenPnP packages
- `sample_parts.xml` - OpenPnP parts
- `sample_easyeda_response.json` - LCSC API response

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src/

# Format code
black src/ tests/
```

## Debugging Tips

1. **OpenPnP not seeing changes**: Ensure OpenPnP is closed before modifying XML files
2. **LCSC API issues**: Check rate limiting, use caching for repeated requests
3. **XML parsing errors**: Validate XML structure matches OpenPnP expectations
4. **GUI freezing**: Move all I/O operations to worker threads

## Reference Links

- OpenPnP Wiki: https://github.com/openpnp/openpnp/wiki
- Package Definitions: https://github.com/openpnp/openpnp/wiki/Package-Definitions
- easyeda2kicad (API reference): https://github.com/uPesy/easyeda2kicad.py
- LCSC Product URLs: https://www.lcsc.com/product-detail/{LCSC_NUMBER}.html
