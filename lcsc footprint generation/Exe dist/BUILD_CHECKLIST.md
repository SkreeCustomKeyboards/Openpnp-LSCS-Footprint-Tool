# Build Checklist for Version 0.2.0

## Pre-Build Verification

- [ ] Version number updated to 0.2.0 in:
  - [x] `src/gui/main_window.py` (About dialog)
  - [x] `dist/create_portable_zip.bat`
  - [x] `CHANGELOG.md`
  - [x] `RELEASE_NOTES_v0.2.0.md`

- [ ] All code changes committed to git
- [ ] CHANGELOG.md is complete and accurate
- [ ] RELEASE_NOTES_v0.2.0.md is finalized

## Build Steps

### 1. Test the Application
```bash
cd "D:\SKREE\Claude-projects\lcsc footprint generation"
python main.py
```

**Test:**
- [ ] Load BOM file
- [ ] Analyze BOM (verify OpenPnP closure warning appears)
- [ ] Process at least one footprint
- [ ] Verify footprint preview shows correctly
- [ ] Write to OpenPnP (verify completion message is correct)
- [ ] Test Restore Backup button
- [ ] Test dark mode toggle
- [ ] Test BOM template export
- [ ] Test About dialog (verify links are clickable)

### 2. Build Portable ZIP
```bash
cd dist
create_portable_zip.bat
```

**Expected output:**
- `OpenPnP_Footprint_Manager_v0.2.0_Portable.zip` created
- Size: ~100-200 KB (source code only)

### 3. Build Standalone EXE
```bash
cd dist
build_exe.bat
```

**Expected output:**
- `dist/OpenPnP_Footprint_Manager.exe` created
- Size: ~150-200 MB (includes Python runtime)

### 4. Or Build Both at Once
```bash
cd dist
build_release.bat
```

## Post-Build Testing

### Test Portable ZIP:
- [ ] Extract ZIP to new folder
- [ ] Double-click `OpenPnP_Footprint_Manager.bat`
- [ ] Verify dependencies install correctly
- [ ] Verify application launches
- [ ] Test basic workflow (load BOM, analyze)

### Test Standalone EXE:
- [ ] Copy `.exe` to clean test folder
- [ ] Double-click to run (no Python should be needed)
- [ ] Verify application launches
- [ ] Test basic workflow

## GitHub Release

### 1. Create Git Tag
```bash
git tag -a v0.2.0 -m "Version 0.2.0 - Y-axis fix and major improvements"
git push origin v0.2.0
```

### 2. Create GitHub Release
- [ ] Go to GitHub repository
- [ ] Click "Releases" → "Create a new release"
- [ ] Tag: `v0.2.0`
- [ ] Title: `OpenPnP Footprint Manager v0.2.0`
- [ ] Description: Copy from `RELEASE_NOTES_v0.2.0.md`
- [ ] Mark as pre-release: No (this is stable)
- [ ] Attach files:
  - [ ] `OpenPnP_Footprint_Manager_v0.2.0_Portable.zip`
  - [ ] `OpenPnP_Footprint_Manager.exe` (rename to `OpenPnP_Footprint_Manager_v0.2.0.exe`)

### 3. Publish Release
- [ ] Click "Publish release"

## Community Announcement

### Post to OpenPnP Discord
- [ ] Use content from `PROGRAM_OVERVIEW.txt`
- [ ] Emphasize the Y-axis bug fix for v0.1.0 users
- [ ] Include download link to GitHub release

### Post to OpenPnP Google Group
- [ ] Same content as Discord
- [ ] Format for email (plain text)

## Post-Release

- [ ] Monitor GitHub issues for bug reports
- [ ] Respond to community feedback
- [ ] Update README.md if needed based on user questions

## Notes

### Known Issues
- None at this time

### Future Improvements
- Footprint caching
- Session persistence
- Batch height/nozzle assignment
- BOM table sorting

---

**Build Date:** _______________
**Built By:** _______________
**Tested By:** _______________
