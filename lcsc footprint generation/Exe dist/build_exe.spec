# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for OpenPnP Footprint Manager
# Usage: pyinstaller build_exe.spec

import sys
from pathlib import Path

# Get the project root directory
project_root = Path(SPECPATH).parent
src_dir = project_root / 'src'
main_script = project_root / 'main.py'

block_cipher = None

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root), str(src_dir)],
    binaries=[],
    datas=[
        # Include sample files if needed
        # (str(project_root / 'Sample files'), 'Sample files'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'httpx',
        'lxml',
        'pandas',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'pytest-qt',
        'mypy',
        'black',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenPnP_Footprint_Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging, False for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you have one
)
