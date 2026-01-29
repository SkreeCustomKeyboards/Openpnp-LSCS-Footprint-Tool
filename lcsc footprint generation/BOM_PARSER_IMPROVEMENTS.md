# BOM Parser Improvements Summary

## Issues Fixed

### 1. CSV Separator Problem
**Issue**: Parser was hardcoded to use tab separator (`\t`) for all CSV files
**Impact**: Comma-separated CSV files failed to parse
**Fix**: Now tries multiple separators in order: comma, tab, semicolon

### 2. UTF-16 Encoding Error
**Issue**: Parser tried UTF-16 encoding first, causing "UTF-16 stream does not start with BOM" error
**Impact**: Standard UTF-8 CSV files failed with confusing error message
**Fix**: Changed priority to try UTF-8 first (most common), then UTF-16

### 3. JLCPCB Column Names
**Issue**: Parser only recognized "LCSC" column variations
**Impact**: BOM files with "JLCPCB Part #" column failed to load
**Fix**: Added JLCPCB variations (same numbering system as LCSC)

## Enhancements Made

### Encoding Support
Now supports:
- UTF-8 (most common)
- UTF-16 and UTF-16-LE (tab-separated exports)
- Latin-1 / ISO-8859-1
- CP1252 (Windows default encoding)

### Separator Support
Now supports:
- Comma `,` (standard CSV)
- Tab `\t` (TSV format)
- Semicolon `;` (European CSV format)

### Column Name Variations

**Reference Column**:
- Reference, Ref, Designator, RefDes, Component, Part Reference

**Value Column**:
- Value, Val, Part Value, Name, Description, Comment

**Footprint Column**:
- FOOTPRINT-NAME, Footprint, Package, Case, PCB Footprint, Footprint Name

**LCSC/JLCPCB Column**:
- supplier part, LCSC, LCSC Part, LCSC#, LCSC Part #
- JLCPCB Part, JLCPCB Part #, JLCPCB, JLCPCB#
- MPN, Manufacturer Part, Part Number

### Robustness Improvements

1. **Whitespace Handling**
   - Trims leading/trailing spaces from column names
   - Uses `skipinitialspace=True` to handle spacing after separators

2. **Empty Row Handling**
   - Automatically skips completely empty rows
   - Skips rows where all values are NA/null

3. **NA Value Detection**
   - Recognizes: '', 'N/A', 'NA', 'null', 'NULL' as empty values
   - Handles pandas default NA values

4. **Data Validation**
   - Checks that parsed DataFrame has multiple columns
   - Verifies at least one data row exists
   - Provides clear error if no valid entries found

5. **Error Recovery**
   - Tries multiple encoding/separator combinations before failing
   - Skips individual rows that can't be parsed (AttributeError, TypeError, etc.)
   - Reports the last error encountered for debugging

## Testing Recommendations

Test with various BOM formats:
- KiCAD export (comma-separated, UTF-8)
- JLCPCB format (with "JLCPCB Part #" column)
- European exports (semicolon separator)
- Excel CSV export (Windows CP1252 encoding)
- Tab-separated exports
- Files with empty rows
- Files with extra whitespace in headers

## Files Modified

- `src/bom/parser.py` - All parsing logic improvements
- `dist/create_portable_zip.bat` - Now includes LICENSE file
- `CHANGELOG.md` - Documented all changes for v0.2.1

## Distribution Files

The distribution build scripts automatically pick up these changes:
- **Portable ZIP**: Copies entire `src/` directory including updated parser
- **Standalone EXE**: PyInstaller spec includes src directory with updated parser

No manual distribution updates needed - just rebuild using existing scripts.
