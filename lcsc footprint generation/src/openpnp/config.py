"""OpenPnP configuration detection and management.

Handles finding and validating OpenPnP configuration directories.
"""

import os
import platform
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


class OpenPnPConfigError(Exception):
    """Error related to OpenPnP configuration."""
    pass


def get_default_openpnp_path() -> Path:
    """Get the default OpenPnP configuration path for the current OS.
    
    Returns:
        Default path to .openpnp2 directory
    """
    system = platform.system()
    home = Path.home()
    
    if system == "Windows":
        return home / ".openpnp2"
    elif system == "Darwin":  # macOS
        return home / ".openpnp2"
    else:  # Linux and others
        return home / ".openpnp2"


def find_openpnp_config() -> Optional[Path]:
    """Find the OpenPnP configuration directory.
    
    Searches in the default location for the current OS.
    
    Returns:
        Path to .openpnp2 directory if found, None otherwise
    """
    default_path = get_default_openpnp_path()
    
    if default_path.exists() and default_path.is_dir():
        # Verify it contains expected files
        if (default_path / "packages.xml").exists() or (default_path / "parts.xml").exists():
            return default_path
    
    return None


def validate_openpnp_config(path: Path) -> bool:
    """Validate that a path is a valid OpenPnP configuration directory.
    
    Args:
        path: Path to validate
        
    Returns:
        True if path appears to be a valid OpenPnP config directory
    """
    if not path.exists():
        return False
    
    if not path.is_dir():
        return False
    
    # Check for at least one expected file
    expected_files = ["machine.xml", "packages.xml", "parts.xml", "vision-settings.xml"]
    for filename in expected_files:
        if (path / filename).exists():
            return True
    
    return False


@dataclass
class OpenPnPConfig:
    """Container for OpenPnP configuration paths and state.
    
    Attributes:
        config_dir: Path to .openpnp2 directory
        packages_file: Path to packages.xml
        parts_file: Path to parts.xml
        machine_file: Path to machine.xml
        backup_dir: Path to backup directory
    """
    config_dir: Path
    
    @property
    def packages_file(self) -> Path:
        """Path to packages.xml."""
        return self.config_dir / "packages.xml"
    
    @property
    def parts_file(self) -> Path:
        """Path to parts.xml."""
        return self.config_dir / "parts.xml"
    
    @property
    def machine_file(self) -> Path:
        """Path to machine.xml."""
        return self.config_dir / "machine.xml"
    
    @property
    def backup_dir(self) -> Path:
        """Path to backup directory within config."""
        return self.config_dir / "backup"
    
    @property
    def footprint_manager_backup_dir(self) -> Path:
        """Path to this application's backup directory."""
        return self.config_dir / "footprint_manager_backups"
    
    def validate(self) -> bool:
        """Validate the configuration.
        
        Returns:
            True if configuration is valid
        """
        return validate_openpnp_config(self.config_dir)
    
    def packages_exists(self) -> bool:
        """Check if packages.xml exists."""
        return self.packages_file.exists()
    
    def parts_exists(self) -> bool:
        """Check if parts.xml exists."""
        return self.parts_file.exists()
    
    def ensure_files_exist(self) -> None:
        """Ensure required XML files exist, creating empty ones if needed.
        
        Raises:
            OpenPnPConfigError: If files cannot be created
        """
        if not self.packages_exists():
            self._create_empty_packages()
        
        if not self.parts_exists():
            self._create_empty_parts()
    
    def _create_empty_packages(self) -> None:
        """Create an empty packages.xml file."""
        content = '<?xml version="1.0" encoding="UTF-8"?>\n<openpnp-packages>\n</openpnp-packages>\n'
        try:
            self.packages_file.write_text(content, encoding="utf-8")
        except IOError as e:
            raise OpenPnPConfigError(f"Failed to create packages.xml: {e}")
    
    def _create_empty_parts(self) -> None:
        """Create an empty parts.xml file."""
        content = '<?xml version="1.0" encoding="UTF-8"?>\n<openpnp-parts>\n</openpnp-parts>\n'
        try:
            self.parts_file.write_text(content, encoding="utf-8")
        except IOError as e:
            raise OpenPnPConfigError(f"Failed to create parts.xml: {e}")
    
    @classmethod
    def from_path(cls, path: Path) -> "OpenPnPConfig":
        """Create OpenPnPConfig from a path.
        
        Args:
            path: Path to .openpnp2 directory
            
        Returns:
            OpenPnPConfig instance
            
        Raises:
            OpenPnPConfigError: If path is invalid
        """
        if not validate_openpnp_config(path):
            raise OpenPnPConfigError(
                f"Invalid OpenPnP configuration directory: {path}"
            )
        return cls(config_dir=path)
    
    @classmethod
    def auto_detect(cls) -> Optional["OpenPnPConfig"]:
        """Auto-detect OpenPnP configuration.
        
        Returns:
            OpenPnPConfig instance if found, None otherwise
        """
        path = find_openpnp_config()
        if path:
            return cls(config_dir=path)
        return None
