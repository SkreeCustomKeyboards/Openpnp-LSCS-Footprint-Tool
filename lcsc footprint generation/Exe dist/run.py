"""
OpenPnP Footprint Manager - Launcher
Checks dependencies and launches the application.
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies_installed():
    """Check if dependencies are already installed."""
    flag_file = Path(__file__).parent / ".dependencies_installed"
    if flag_file.exists():
        return True

    # Quick check for PyQt6 (main dependency)
    try:
        import PyQt6
        return True
    except ImportError:
        return False

def run_dependency_installer():
    """Run the dependency installer script."""
    installer = Path(__file__).parent / "install_dependencies.py"
    result = subprocess.run([sys.executable, str(installer)])
    return result.returncode == 0

def launch_application():
    """Launch the main application."""
    # Add current directory to path to import src modules
    app_root = Path(__file__).parent
    sys.path.insert(0, str(app_root))

    main_script = app_root / "main.py"

    if not main_script.exists():
        print(f"ERROR: main.py not found at {main_script}")
        input("Press Enter to exit...")
        return False

    try:
        # Import and run the main application
        import runpy
        sys.argv[0] = str(main_script)
        runpy.run_path(str(main_script), run_name="__main__")
        return True

    except Exception as e:
        print(f"ERROR: Failed to launch application: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        return False

def main():
    """Main launcher routine."""
    # Check if dependencies are installed
    if not check_dependencies_installed():
        print("Dependencies not installed. Running installer...")
        if not run_dependency_installer():
            print("\nFailed to install dependencies.")
            input("Press Enter to exit...")
            return False

    # Launch the application
    return launch_application()

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
