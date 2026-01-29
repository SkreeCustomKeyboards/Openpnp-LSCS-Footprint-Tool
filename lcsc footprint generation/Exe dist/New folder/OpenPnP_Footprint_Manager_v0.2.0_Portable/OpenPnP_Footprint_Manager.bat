@echo off
REM OpenPnP Footprint Manager - Windows Launcher
REM This batch file launches the application with dependency checking

title OpenPnP Footprint Manager

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Run the launcher script
python "%~dp0run.py"

REM Keep window open if there was an error
if errorlevel 1 (
    pause
)
