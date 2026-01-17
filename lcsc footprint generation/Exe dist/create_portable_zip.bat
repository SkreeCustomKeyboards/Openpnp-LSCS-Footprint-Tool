@echo off
REM Create a portable ZIP distribution of OpenPnP Footprint Manager

title Creating Portable ZIP Distribution

echo ============================================================
echo Creating OpenPnP Footprint Manager - Portable ZIP
echo ============================================================
echo.

REM Set version (update this for each release)
set VERSION=0.2.0
set DIST_NAME=OpenPnP_Footprint_Manager_v%VERSION%_Portable

REM Create temporary distribution folder
echo Creating distribution folder...
if exist "%DIST_NAME%" rmdir /s /q "%DIST_NAME%"
mkdir "%DIST_NAME%"

REM Copy necessary files from parent directory
echo Copying application files...
xcopy /E /I /Y "..\src" "%DIST_NAME%\src"
copy "..\main.py" "%DIST_NAME%\"
copy "..\README.md" "%DIST_NAME%\"
copy "..\CLAUDE.md" "%DIST_NAME%\"

REM Copy dist folder files
echo Copying launcher files...
copy "requirements-runtime.txt" "%DIST_NAME%\"
copy "install_dependencies.py" "%DIST_NAME%\"
copy "run.py" "%DIST_NAME%\"
copy "OpenPnP_Footprint_Manager.bat" "%DIST_NAME%\"
copy "README_DISTRIBUTION.md" "%DIST_NAME%\README.md"

REM Create Sample files folder (optional)
if exist "..\Sample files" (
    echo Copying sample files...
    xcopy /E /I /Y "..\Sample files" "%DIST_NAME%\Sample files"
)

REM Create ZIP file (requires PowerShell)
echo.
echo Creating ZIP archive...
powershell -Command "Compress-Archive -Path '%DIST_NAME%' -DestinationPath '%DIST_NAME%.zip' -Force"

if exist "%DIST_NAME%.zip" (
    REM Get file size
    for %%I in ("%DIST_NAME%.zip") do set SIZE=%%~zI
    set /a SIZE_MB=%SIZE% / 1048576

    echo.
    echo ============================================================
    echo Portable ZIP created successfully!
    echo ============================================================
    echo.
    echo File: %CD%\%DIST_NAME%.zip
    echo Size: ~%SIZE_MB% MB
    echo.
    echo This ZIP contains:
    echo - Python source code
    echo - Auto-dependency installer
    echo - Windows launcher (.bat)
    echo - Documentation
    echo.
    echo Users need: Python 3.10+ installed
    echo.

    REM Ask if we should clean up temp folder
    set /p CLEANUP="Delete temporary folder? (Y/n): "
    if /i "%CLEANUP%"=="n" (
        echo Keeping %DIST_NAME% folder
    ) else (
        rmdir /s /q "%DIST_NAME%"
        echo Cleaned up temporary folder
    )
) else (
    echo ERROR: Failed to create ZIP file
)

echo.
pause
