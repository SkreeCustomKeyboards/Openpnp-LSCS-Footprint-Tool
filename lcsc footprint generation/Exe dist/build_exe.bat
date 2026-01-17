@echo off
REM Build standalone executable using PyInstaller

title Building OpenPnP Footprint Manager EXE

echo ============================================================
echo Building OpenPnP Footprint Manager - Standalone Executable
echo ============================================================
echo.

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist "dist\OpenPnP_Footprint_Manager.exe" del "dist\OpenPnP_Footprint_Manager.exe"

REM Build the executable
echo.
echo Building executable...
echo This may take several minutes...
echo.

python -m PyInstaller build_exe.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed
    pause
    exit /b 1
)

REM Check if exe was created
if exist "dist\OpenPnP_Footprint_Manager.exe" (
    echo.
    echo ============================================================
    echo Build completed successfully!
    echo ============================================================
    echo.
    echo Executable location:
    echo %CD%\dist\OpenPnP_Footprint_Manager.exe
    echo.
    echo File size:
    dir "dist\OpenPnP_Footprint_Manager.exe" | find "OpenPnP"
    echo.
    echo You can now distribute the .exe file to other Windows users.
    echo No Python installation required on target machines.
    echo.
) else (
    echo ERROR: Executable was not created
)

pause
