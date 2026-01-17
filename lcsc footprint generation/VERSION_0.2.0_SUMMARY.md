# Version 0.2.0 - Complete Summary

**Release Date:** January 16, 2025
**Version:** 0.2.0
**Previous Version:** 0.1.0

## Quick Stats
- **Critical Bugs Fixed:** 1 (Y-axis inversion)
- **Regressions Fixed:** 1 (Nozzle replacement)
- **New Features:** 5 (Dark mode, BOM template, backup management, warnings, About enhancements)
- **Files Modified:** 8
- **Lines of Code Changed:** ~200+

## Critical Changes

### 1. Y-Axis Coordinate Inversion Fix (CRITICAL)
**Impact:** ALL v0.1.0 footprints are incorrect and must be re-imported

**Technical Details:**
- File: `src/scraper/footprint_parser.py:308`
- Change: Added `y_mm = -eda_pad.y * self.UNITS_TO_MM`
- Reason: EasyEDA uses Y-up, OpenPnP uses Y-down
- Testing: Verified with C730243 (QFN-16)

**User Action Required:**
1. Restore backup from before v0.1.0 import
2. Re-import all footprints with v0.2.0
3. Verify pin 1 orientation

### 2. OpenPnP Closure Warnings (CRITICAL)
**Impact:** Prevents data loss

**Changes:**
- Added warning dialog before BOM analysis
- Updated write completion message
- Clear instructions about when OpenPnP can be opened

## New Features

### 1. Dark Mode
- Toggle in View menu
- Complete theme for all UI elements
- Professional color scheme

### 2. BOM Template Export
- File → Export BOM Template
- Creates CSV with correct headers
- Includes sample data

### 3. Enhanced Backup Management
- "Create Backup" button
- "Navigate to Backups" button
- Restore available immediately on startup

### 4. Improved About Dialog
- Clickable GitHub link
- Clickable OpenPnP link
- Selectable text
- Credits and legal notice

## Bug Fixes

### 1. Restore Backup Button
- Now enabled on startup if backups exist
- Previously required BOM load first

### 2. Nozzle Tip Replacement
- Fixed regression from earlier session
- Properly removes old nozzle before adding new
- Updates Package object directly

### 3. Pad Roundness
- Round/circular pads: 100
- Oval pads: 50
- Rectangular pads: 0
- Respects EasyEDA shape data

## Files Modified

1. **src/gui/main_window.py**
   - Version number: 0.2.0
   - OpenPnP closure warnings
   - Dark mode toggle
   - BOM template export
   - Backup management buttons
   - About dialog enhancements
   - Nozzle replacement fix
   - Restore button fix

2. **src/scraper/footprint_parser.py**
   - Y-axis inversion fix
   - Roundness shape detection

3. **CHANGELOG.md**
   - Complete v0.2.0 changelog

4. **RELEASE_NOTES_v0.2.0.md**
   - Comprehensive release notes
   - Upgrade instructions
   - Verification checklist

5. **PROGRAM_OVERVIEW.txt**
   - Community announcement text

6. **docs/COORDINATE_SYSTEM_FIX.md**
   - Technical documentation of Y-axis fix

7. **dist/create_portable_zip.bat**
   - Version updated to 0.2.0

8. **dist/README_DISTRIBUTION.md**
   - Version updated
   - OpenPnP closure warning added

## New Files Created

1. **dist/build_release.bat** - Automated release build script
2. **dist/BUILD_CHECKLIST.md** - Release checklist
3. **VERSION_0.2.0_SUMMARY.md** - This file

## Testing Completed

- ✅ Y-axis inversion verified with C730243
- ✅ Roundness values correct (0, 50, 100)
- ✅ Nozzle replacement works correctly
- ✅ Restore backup available on startup
- ✅ Dark mode toggles correctly
- ✅ BOM template exports correctly
- ✅ About dialog links are clickable
- ✅ OpenPnP warnings display correctly

## Known Issues

None at this time.

## Distribution

### Portable ZIP
- **File:** `OpenPnP_Footprint_Manager_v0.2.0_Portable.zip`
- **Size:** ~100-200 KB
- **Requires:** Python 3.10+
- **Build:** `cd dist && create_portable_zip.bat`

### Standalone EXE
- **File:** `OpenPnP_Footprint_Manager.exe`
- **Size:** ~150-200 MB
- **Requires:** Nothing (Python bundled)
- **Build:** `cd dist && build_exe.bat`

### Build Both
- **Command:** `cd dist && build_release.bat`

## Release Workflow

1. **Pre-Build Testing**
   - Test all features
   - Verify warnings work
   - Test backup/restore
   - Test dark mode
   - Test BOM template

2. **Build**
   - Run `build_release.bat`
   - Verify both distributions created

3. **Post-Build Testing**
   - Test portable ZIP on clean system
   - Test standalone EXE on clean system

4. **GitHub Release**
   - Create tag v0.2.0
   - Upload distributions
   - Copy release notes

5. **Community Announcement**
   - Post to OpenPnP Discord
   - Post to OpenPnP Google Group
   - Emphasize Y-axis bug fix

## Support

- **GitHub Issues:** https://github.com/SkreeCustomKeyboards/Openpnp-LSCS-Footprint-Tool/issues
- **Documentation:** See README.md and docs/ folder

## Credits

**Created by:** Skree LLC - Marshall Somerville
**With:** Claude Code
**License:** [See main README.md]

---

**This release is production-ready and stable.**
