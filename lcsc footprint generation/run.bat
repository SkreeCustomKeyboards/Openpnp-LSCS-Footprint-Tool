@echo off
REM OpenPnP Footprint Manager Launcher
REM This batch file launches the OpenPnP Footprint Manager application

echo Starting OpenPnP Footprint Manager...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Run the application
python "%~dp0main.py"

REM If the application exits with an error, pause so user can see the error
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
