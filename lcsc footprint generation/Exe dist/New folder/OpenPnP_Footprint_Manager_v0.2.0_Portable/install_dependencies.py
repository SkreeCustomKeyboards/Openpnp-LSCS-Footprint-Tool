"""
OpenPnP Footprint Manager - Dependency Installer
Checks for and installs required dependencies on first run.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.10 or higher."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"ERROR: Python 3.10 or higher is required.")
        print(f"You are using Python {version.major}.{version.minor}.{version.micro}")
        print("\nPlease download Python 3.10+ from https://www.python.org/downloads/")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_pip():
    """Check if pip is available."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                      capture_output=True, check=True)
        print("✓ pip is available")
        return True
    except subprocess.CalledProcessError:
        print("ERROR: pip is not available")
        print("Please install pip: python -m ensurepip --upgrade")
        return False

def install_dependencies():
    """Install required dependencies from requirements-runtime.txt."""
    requirements_file = Path(__file__).parent / "requirements-runtime.txt"

    if not requirements_file.exists():
        print(f"ERROR: requirements-runtime.txt not found at {requirements_file}")
        return False

    print("\n" + "="*60)
    print("Installing dependencies...")
    print("="*60 + "\n")

    try:
        # Upgrade pip first
        print("Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                      check=True)

        # Install dependencies
        print(f"\nInstalling from {requirements_file}...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                      check=True)

        print("\n" + "="*60)
        print("✓ All dependencies installed successfully!")
        print("="*60)
        return True

    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Failed to install dependencies: {e}")
        return False

def check_dependencies():
    """Check if all required packages are installed."""
    required_packages = [
        "PyQt6",
        "httpx",
        "lxml",
        "pandas",
        "openpyxl"
    ]

    missing = []
    print("\nChecking installed packages...")

    for package in required_packages:
        try:
            __import__(package.lower().replace("-", "_"))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (missing)")
            missing.append(package)

    return len(missing) == 0, missing

def create_flag_file():
    """Create a flag file to indicate dependencies are installed."""
    flag_file = Path(__file__).parent / ".dependencies_installed"
    flag_file.touch()

def main():
    """Main dependency installation routine."""
    print("="*60)
    print("OpenPnP Footprint Manager - Dependency Checker")
    print("="*60 + "\n")

    # Check Python version
    if not check_python_version():
        input("\nPress Enter to exit...")
        return False

    # Check pip
    if not check_pip():
        input("\nPress Enter to exit...")
        return False

    # Check if dependencies are installed
    deps_ok, missing = check_dependencies()

    if deps_ok:
        print("\n✓ All dependencies are already installed!")
        create_flag_file()
        return True

    # Ask user if they want to install
    print(f"\nMissing packages: {', '.join(missing)}")
    response = input("\nInstall missing dependencies? (Y/n): ").strip().lower()

    if response in ['', 'y', 'yes']:
        if install_dependencies():
            # Verify installation
            deps_ok, missing = check_dependencies()
            if deps_ok:
                create_flag_file()
                print("\n✓ Ready to run OpenPnP Footprint Manager!")
                return True
            else:
                print(f"\nWARNING: Some packages still missing: {', '.join(missing)}")
                return False
        else:
            return False
    else:
        print("\nDependencies not installed. Cannot run application.")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
