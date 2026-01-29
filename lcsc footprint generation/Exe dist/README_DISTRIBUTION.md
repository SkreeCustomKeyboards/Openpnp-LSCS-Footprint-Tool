# OpenPnP Footprint Manager - Distribution Guide (v0.2.0)

This folder contains everything needed to distribute and run the OpenPnP Footprint Manager.

## ⚠️ CRITICAL USAGE REQUIREMENT

**OpenPnP MUST be closed before running this tool!**

If OpenPnP is running when you use this tool, all changes will be lost when OpenPnP closes, as OpenPnP will overwrite the files this tool modifies. Always close OpenPnP before analyzing and importing footprints.

## Distribution Options

### Option 1: Python Script with Auto-Installer (Smallest, Requires Python)

**Best for:** Users who have Python installed or are comfortable installing it.

**Distribution:**
1. Copy entire project folder
2. User double-clicks `OpenPnP_Footprint_Manager.bat` (Windows)
3. On first run, dependencies are automatically checked and installed

**Pros:**
- Smallest distribution size (~50KB without Python)
- Easy to update (just replace files)
- Users can see and modify source code

**Cons:**
- Requires Python 3.10+ on target machine
- First-run dependency installation takes a few minutes

**Usage:**
```
1. Install Python 3.10+ from https://www.python.org/downloads/
2. Double-click "OpenPnP_Footprint_Manager.bat"
3. Follow on-screen prompts to install dependencies (first run only)
4. Application launches automatically
```

---

### Option 2: Standalone Executable (Largest, No Python Required)

**Best for:** End users who don't have Python and want simplest installation.

**Build Instructions:**
1. Install dependencies: `pip install -r requirements-runtime.txt`
2. Install PyInstaller: `pip install pyinstaller`
3. Run `build_exe.bat`
4. Distribute the generated `.exe` file from the `dist` folder

**Pros:**
- No Python installation required on target machine
- Single file to distribute
- Professional appearance

**Cons:**
- Large file size (~150-200MB)
- Longer startup time (unpacks on each run)
- Harder to update (must rebuild entire exe)

**Build Command:**
```batch
build_exe.bat
```

Or manually:
```batch
pyinstaller build_exe.spec
```

---

### Option 3: Portable Python Bundle (Advanced)

**Best for:** Organizations wanting a portable, no-install solution.

**Setup:**
1. Download Python embeddable package from python.org
2. Extract to `dist/python/`
3. Install dependencies: `python/python.exe -m pip install -r requirements-runtime.txt`
4. Create launcher that uses `dist/python/python.exe`

**Pros:**
- No system installation required
- Includes Python interpreter
- More control over environment

**Cons:**
- Medium file size (~200-250MB)
- More complex initial setup

---

## Files in This Folder

### Core Files
- `requirements-runtime.txt` - List of required Python packages
- `install_dependencies.py` - Automatic dependency installer script
- `run.py` - Application launcher with dependency checking
- `OpenPnP_Footprint_Manager.bat` - Windows launcher (double-click to run)

### Build Files
- `build_exe.spec` - PyInstaller configuration for building standalone .exe
- `build_exe.bat` - Automated build script for Windows

### Generated Files (after first run)
- `.dependencies_installed` - Flag file indicating dependencies are ready

---

## Quick Start for End Users

### Windows Users:
1. **If you have Python 3.10+ installed:**
   - Double-click `OpenPnP_Footprint_Manager.bat`

2. **If you don't have Python:**
   - Option A: Install Python 3.10+ from https://www.python.org/downloads/ then use method 1
   - Option B: Get the standalone `.exe` file (if available)

### Linux/macOS Users:
```bash
# Install dependencies
python3 -m pip install -r requirements-runtime.txt

# Run application
python3 ../main.py
```

---

## Dependency Details

### Required Packages:
- **PyQt6** (6.4.0+) - GUI framework
- **httpx** (0.24.0+) - HTTP client for LCSC API
- **lxml** (4.9.0+) - XML parsing for OpenPnP files
- **pandas** (2.0.0+) - BOM file parsing
- **openpyxl** (3.1.0+) - Excel file support

### Install Command:
```bash
pip install -r requirements-runtime.txt
```

---

## Troubleshooting

### "Python is not installed or not in PATH"
- Install Python 3.10 or higher from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- Restart your terminal/command prompt after installation

### Dependencies fail to install
- Try updating pip first: `python -m pip install --upgrade pip`
- Run with admin privileges if on Windows
- Check internet connection (packages download from PyPI)

### Application won't start
- Run `install_dependencies.py` manually to see detailed error messages
- Check Python version: `python --version` (must be 3.10+)
- Verify all dependencies: `python -c "import PyQt6, httpx, lxml, pandas, openpyxl"`

### Standalone .exe is slow to start
- This is normal - PyInstaller unpacks files on each run
- First run is slower than subsequent runs

---

## Building for Distribution

### For Developers:

**To create a portable Python version:**
```batch
# Create distribution folder
python -m venv dist/venv
dist/venv/Scripts/activate
pip install -r requirements-runtime.txt

# Update launcher to use dist/venv/Scripts/python.exe
```

**To create standalone executable:**
```batch
cd dist
build_exe.bat
```

**To create an installer:**
- Use Inno Setup or NSIS with the standalone .exe
- Include Visual C++ Redistributable if needed

---

## Platform Support

### Current Support:
- ✅ Windows 10/11 (fully tested)

### Planned Support:
- 🔄 Linux (Python script works, needs testing)
- 🔄 macOS (Python script works, needs testing)

### Notes:
- PyQt6 is cross-platform, so the application should work on Linux/macOS
- OpenPnP configuration paths are OS-specific and already handled in the code
- For Linux/macOS, use the Python script option (Option 1)

---

## File Size Comparison

| Distribution Method | Size | Python Required | First-Run Time |
|---------------------|------|-----------------|----------------|
| Python Script       | ~50KB | Yes (3.10+)    | 2-3 min (install deps) |
| Standalone EXE      | ~150-200MB | No         | 5-10 sec (first run) |
| Portable Bundle     | ~200-250MB | Bundled    | 2-3 sec |

---

## License

This application is distributed under the same license as the main project.
See the project README.md for license information.
