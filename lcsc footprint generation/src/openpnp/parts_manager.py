"""Manager for OpenPnP parts.xml file.

Handles reading, writing, and modifying part definitions.
"""

from pathlib import Path
from typing import Optional, Dict
from lxml import etree
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.part import Part


class PartsManagerError(Exception):
    """Error in parts management."""
    pass


class PartsManager:
    """Manages OpenPnP parts.xml file.
    
    Provides methods to read, modify, and write part definitions.
    """
    
    def __init__(self, parts_file: Path):
        """Initialize parts manager.
        
        Args:
            parts_file: Path to parts.xml
        """
        self._filepath = parts_file
        self._parts: Dict[str, Part] = {}
        self._tree: Optional[etree._ElementTree] = None
        self._root: Optional[etree._Element] = None
        self._modified = False
    
    @property
    def filepath(self) -> Path:
        """Path to parts.xml."""
        return self._filepath
    
    @property
    def is_loaded(self) -> bool:
        """Check if parts are loaded."""
        return self._root is not None
    
    @property
    def is_modified(self) -> bool:
        """Check if parts have been modified since load."""
        return self._modified
    
    def load(self) -> None:
        """Load parts from XML file.
        
        Raises:
            PartsManagerError: If loading fails
        """
        if not self._filepath.exists():
            # Create empty structure
            self._root = etree.Element("openpnp-parts")
            self._tree = etree.ElementTree(self._root)
            self._parts = {}
            return
        
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            self._tree = etree.parse(str(self._filepath), parser)
            self._root = self._tree.getroot()
        except etree.XMLSyntaxError as e:
            raise PartsManagerError(f"Invalid XML in parts.xml: {e}")
        except IOError as e:
            raise PartsManagerError(f"Failed to read parts.xml: {e}")
        
        # Parse parts
        self._parts = {}
        for part_elem in self._root.findall("part"):
            try:
                part = Part.from_xml_element(part_elem)
                self._parts[part.id] = part
            except (KeyError, ValueError):
                # Skip malformed parts
                continue
        
        self._modified = False
    
    def save(self) -> None:
        """Save parts to XML file.
        
        Raises:
            PartsManagerError: If saving fails
        """
        if self._root is None:
            raise PartsManagerError("No parts loaded")
        
        try:
            self._tree.write(
                str(self._filepath),
                encoding="UTF-8",
                xml_declaration=True,
                pretty_print=True
            )
            self._modified = False
        except IOError as e:
            raise PartsManagerError(f"Failed to write parts.xml: {e}")
    
    def get_part(self, part_id: str) -> Optional[Part]:
        """Get a part by ID.
        
        Args:
            part_id: Part identifier
            
        Returns:
            Part if found, None otherwise
        """
        return self._parts.get(part_id)
    
    def has_part(self, part_id: str) -> bool:
        """Check if a part exists.
        
        Args:
            part_id: Part identifier
            
        Returns:
            True if part exists
        """
        return part_id in self._parts
    
    def list_parts(self) -> list[str]:
        """List all part IDs.
        
        Returns:
            List of part IDs
        """
        return list(self._parts.keys())
    
    def add_part(self, part: Part) -> None:
        """Add a new part.
        
        Args:
            part: Part to add
            
        Raises:
            PartsManagerError: If part already exists
        """
        if self._root is None:
            raise PartsManagerError("No parts loaded")
        
        if part.id in self._parts:
            raise PartsManagerError(f"Part already exists: {part.id}")
        
        # Add to XML tree
        part_elem = part.to_xml_element()
        self._root.append(part_elem)
        
        # Add to internal dict
        self._parts[part.id] = part
        self._modified = True
    
    def update_part(self, part: Part) -> None:
        """Update an existing part.
        
        Args:
            part: Part with updated data
            
        Raises:
            PartsManagerError: If part doesn't exist
        """
        if self._root is None:
            raise PartsManagerError("No parts loaded")
        
        if part.id not in self._parts:
            raise PartsManagerError(f"Part not found: {part.id}")
        
        # Find and remove old element
        for elem in self._root.findall("part"):
            if elem.get("id") == part.id:
                self._root.remove(elem)
                break
        
        # Add updated element
        part_elem = part.to_xml_element()
        self._root.append(part_elem)
        
        # Update internal dict
        self._parts[part.id] = part
        self._modified = True
    
    def remove_part(self, part_id: str) -> None:
        """Remove a part.
        
        Args:
            part_id: ID of part to remove
            
        Raises:
            PartsManagerError: If part doesn't exist
        """
        if self._root is None:
            raise PartsManagerError("No parts loaded")
        
        if part_id not in self._parts:
            raise PartsManagerError(f"Part not found: {part_id}")
        
        # Remove from XML tree
        for elem in self._root.findall("part"):
            if elem.get("id") == part_id:
                self._root.remove(elem)
                break
        
        # Remove from internal dict
        del self._parts[part_id]
        self._modified = True
    
    def get_part_count(self) -> int:
        """Get the number of parts.
        
        Returns:
            Number of parts
        """
        return len(self._parts)
    
    def find_parts_by_package(self, package_id: str) -> list[Part]:
        """Find all parts using a specific package.
        
        Args:
            package_id: Package identifier
            
        Returns:
            List of parts using that package
        """
        return [p for p in self._parts.values() if p.package_id == package_id]
    
    def get_used_packages(self) -> set[str]:
        """Get set of all package IDs used by parts.
        
        Returns:
            Set of package IDs
        """
        return {p.package_id for p in self._parts.values()}
