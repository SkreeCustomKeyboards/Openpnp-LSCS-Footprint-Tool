@echo off
REM Build release package for OpenPnP Footprint Manager v0.2.0
REM This script creates both the portable ZIP and standalone EXE

title Building OpenPnP Footprint Manager v0.2.0 Release

echo ============================================================
echo Building OpenPnP Footprint Manager v0.2.0
echo ============================================================
echo.
echo This will create:
echo 1. Portable ZIP (Python source with auto-installer)
echo 2. Standalone EXE (Windows only, no Python required)
echo.
pause

REM Step 1: Create Portable ZIP
echo.
echo ============================================================
echo Step 1: Creating Portable ZIP
echo ============================================================
call create_portable_zip.bat

if errorlevel 1 (
    echo ERROR: Portable ZIP creation failed
    pause
    exit /b 1
)

REM Step 2: Build Standalone EXE
echo.
echo ============================================================
echo Step 2: Building Standalone EXE
echo ============================================================
call build_exe.bat

if errorlevel 1 (
    echo ERROR: EXE build failed
    pause
    exit /b 1
)

REM Step 3: Show summary
echo.
echo ============================================================
echo Release Build Complete!
echo ============================================================
echo.
echo Files created:
echo.
echo Portable ZIP:
dir /b OpenPnP_Footprint_Manager_v0.2.0_Portable.zip 2>nul
if errorlevel 1 (
    echo   [NOT FOUND]
) else (
    for %%I in (OpenPnP_Footprint_Manager_v0.2.0_Portable.zip) do echo   %%~nI%%~xI - %%~zI bytes
)
echo.
echo Standalone EXE:
dir /b dist\OpenPnP_Footprint_Manager.exe 2>nul
if errorlevel 1 (
    echo   [NOT FOUND]
) else (
    for %%I in (dist\OpenPnP_Footprint_Manager.exe) do echo   %%~nI%%~xI - %%~zI bytes
)
echo.
echo ============================================================
echo Next Steps:
echo ============================================================
echo 1. Test both distributions
echo 2. Create GitHub release v0.2.0
echo 3. Upload both files to GitHub
echo 4. Post announcement to OpenPnP Discord/Google Group
echo.
echo See RELEASE_NOTES_v0.2.0.md for release announcement
echo.
pause
