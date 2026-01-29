"""Manager for OpenPnP packages.xml file.

Handles reading, writing, and modifying package (footprint) definitions.
"""

from pathlib import Path
from typing import Optional, Dict
from lxml import etree
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.footprint import Package, Footprint, Pad


class PackagesManagerError(Exception):
    """Error in packages management."""
    pass


class PackagesManager:
    """Manages OpenPnP packages.xml file.
    
    Provides methods to read, modify, and write package definitions.
    """
    
    def __init__(self, packages_file: Path):
        """Initialize packages manager.
        
        Args:
            packages_file: Path to packages.xml
        """
        self._filepath = packages_file
        self._packages: Dict[str, Package] = {}
        self._tree: Optional[etree._ElementTree] = None
        self._root: Optional[etree._Element] = None
        self._modified = False
    
    @property
    def filepath(self) -> Path:
        """Path to packages.xml."""
        return self._filepath
    
    @property
    def is_loaded(self) -> bool:
        """Check if packages are loaded."""
        return self._root is not None
    
    @property
    def is_modified(self) -> bool:
        """Check if packages have been modified since load."""
        return self._modified
    
    def load(self) -> None:
        """Load packages from XML file.
        
        Raises:
            PackagesManagerError: If loading fails
        """
        if not self._filepath.exists():
            # Create empty file
            self._root = etree.Element("openpnp-packages")
            self._tree = etree.ElementTree(self._root)
            self._packages = {}
            return
        
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            self._tree = etree.parse(str(self._filepath), parser)
            self._root = self._tree.getroot()
        except etree.XMLSyntaxError as e:
            raise PackagesManagerError(f"Invalid XML in packages.xml: {e}")
        except IOError as e:
            raise PackagesManagerError(f"Failed to read packages.xml: {e}")
        
        # Parse packages
        self._packages = {}
        for package_elem in self._root.findall("package"):
            try:
                package = Package.from_xml_element(package_elem)
                self._packages[package.id] = package
            except (KeyError, ValueError) as e:
                # Skip malformed packages
                continue
        
        self._modified = False
    
    def save(self) -> None:
        """Save packages to XML file.
        
        Raises:
            PackagesManagerError: If saving fails
        """
        if self._root is None:
            raise PackagesManagerError("No packages loaded")
        
        try:
            # Write with proper formatting
            self._tree.write(
                str(self._filepath),
                encoding="UTF-8",
                xml_declaration=True,
                pretty_print=True
            )
            self._modified = False
        except IOError as e:
            raise PackagesManagerError(f"Failed to write packages.xml: {e}")
    
    def get_package(self, package_id: str) -> Optional[Package]:
        """Get a package by ID.
        
        Args:
            package_id: Package identifier
            
        Returns:
            Package if found, None otherwise
        """
        return self._packages.get(package_id)
    
    def has_package(self, package_id: str) -> bool:
        """Check if a package exists.
        
        Args:
            package_id: Package identifier
            
        Returns:
            True if package exists
        """
        return package_id in self._packages
    
    def list_packages(self) -> list[str]:
        """List all package IDs.
        
        Returns:
            List of package IDs
        """
        return list(self._packages.keys())
    
    def add_package(self, package: Package) -> None:
        """Add a new package.
        
        Args:
            package: Package to add
            
        Raises:
            PackagesManagerError: If package already exists
        """
        if self._root is None:
            raise PackagesManagerError("No packages loaded")
        
        if package.id in self._packages:
            raise PackagesManagerError(f"Package already exists: {package.id}")
        
        # Add to XML tree
        package_elem = package.to_xml_element()
        self._root.append(package_elem)
        
        # Add to internal dict
        self._packages[package.id] = package
        self._modified = True
    
    def update_package(self, package: Package) -> None:
        """Update an existing package.
        
        Args:
            package: Package with updated data
            
        Raises:
            PackagesManagerError: If package doesn't exist
        """
        if self._root is None:
            raise PackagesManagerError("No packages loaded")
        
        if package.id not in self._packages:
            raise PackagesManagerError(f"Package not found: {package.id}")
        
        # Find and remove old element
        for elem in self._root.findall("package"):
            if elem.get("id") == package.id:
                self._root.remove(elem)
                break
        
        # Add updated element
        package_elem = package.to_xml_element()
        self._root.append(package_elem)
        
        # Update internal dict
        self._packages[package.id] = package
        self._modified = True
    
    def remove_package(self, package_id: str) -> None:
        """Remove a package.
        
        Args:
            package_id: ID of package to remove
            
        Raises:
            PackagesManagerError: If package doesn't exist
        """
        if self._root is None:
            raise PackagesManagerError("No packages loaded")
        
        if package_id not in self._packages:
            raise PackagesManagerError(f"Package not found: {package_id}")
        
        # Remove from XML tree
        for elem in self._root.findall("package"):
            if elem.get("id") == package_id:
                self._root.remove(elem)
                break
        
        # Remove from internal dict
        del self._packages[package_id]
        self._modified = True
    
    def get_package_count(self) -> int:
        """Get the number of packages.
        
        Returns:
            Number of packages
        """
        return len(self._packages)
    
    def find_similar_packages(self, base_name: str) -> list[Package]:
        """Find packages with similar names.
        
        Useful for finding existing footprints that might be reusable.
        
        Args:
            base_name: Base name to search for (e.g., "0402", "SOT-23")
            
        Returns:
            List of packages with matching base names
        """
        similar = []
        base_lower = base_name.lower()
        
        for package_id, package in self._packages.items():
            if base_lower in package_id.lower():
                similar.append(package)
        
        return similar
