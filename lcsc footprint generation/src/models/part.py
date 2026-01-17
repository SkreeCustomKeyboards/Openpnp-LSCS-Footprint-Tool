"""Part and BOM entry data models.

These models represent parts (components) and BOM entries.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto
from lxml import etree


class PartStatus(Enum):
    """Status of a part in the processing queue."""
    PENDING = auto()      # Not yet processed
    EXISTS = auto()       # Already exists in OpenPnP
    CREATED = auto()      # Successfully created
    SKIPPED = auto()      # Skipped by user
    ERROR = auto()        # Error during processing
    NO_LCSC = auto()      # No LCSC number provided


@dataclass
class Part:
    """Represents an OpenPnP part definition.

    A part is a specific component that references a package (footprint).

    Attributes:
        id: Unique part identifier (e.g., "R0402-10K")
        package_id: Reference to package in packages.xml
        height: Component height in mm (for nozzle clearance)
        speed: Placement speed multiplier (1.0 = normal)
        height_units: Unit system for height (always "Millimeters")
        name: Optional part name/description (e.g., LCSC part number)
        generator: Tool that generated this part (for tracking)
        import_date: ISO format date of import
        session_id: Unique session identifier for bulk operations
        lcsc_id: LCSC part number reference
    """
    id: str
    package_id: str
    height: float = 0.5
    speed: float = 1.0
    height_units: str = "Millimeters"
    name: Optional[str] = None
    generator: Optional[str] = None
    import_date: Optional[str] = None
    session_id: Optional[str] = None
    lcsc_id: Optional[str] = None
    
    def to_xml_element(self) -> etree._Element:
        """Convert part to OpenPnP XML element.

        Returns:
            lxml Element representing the part
        """
        attribs = {
            "id": self.id,
            "height-units": self.height_units,
            "height": f"{self.height:.2f}",
            "package-id": self.package_id,
            "speed": f"{self.speed:.1f}"
        }

        # Add name if provided
        if self.name:
            attribs["name"] = self.name

        part_elem = etree.Element("part", **attribs)

        # Add metadata as XML comment for tracking (OpenPnP doesn't support custom attributes)
        if self.generator or self.import_date or self.session_id or self.lcsc_id:
            metadata_parts = []
            if self.generator:
                metadata_parts.append(f"generator={self.generator}")
            if self.import_date:
                metadata_parts.append(f"import_date={self.import_date}")
            if self.session_id:
                metadata_parts.append(f"session_id={self.session_id}")
            if self.lcsc_id:
                metadata_parts.append(f"lcsc_id={self.lcsc_id}")

            comment_text = " | ".join(metadata_parts)
            comment = etree.Comment(f" {comment_text} ")
            part_elem.append(comment)

        return part_elem
    
    @classmethod
    def from_xml_element(cls, element: etree._Element) -> "Part":
        """Create Part from OpenPnP XML element.
        
        Args:
            element: lxml Element containing part data
            
        Returns:
            Part instance
        """
        return cls(
            id=element.get("id", ""),
            package_id=element.get("package-id", ""),
            height=float(element.get("height", 0.5)),
            speed=float(element.get("speed", 1.0)),
            height_units=element.get("height-units", "Millimeters"),
            generator=element.get("x-generator"),
            import_date=element.get("x-import-date"),
            session_id=element.get("x-session-id"),
            lcsc_id=element.get("x-lcsc-id")
        )
    
    def to_xml_string(self, pretty: bool = True) -> str:
        """Convert part to XML string.
        
        Args:
            pretty: If True, format with indentation
            
        Returns:
            XML string representation
        """
        element = self.to_xml_element()
        return etree.tostring(
            element,
            pretty_print=pretty,
            encoding="unicode"
        )


@dataclass
class BomEntry:
    """Represents a single entry from a BOM file.
    
    Attributes:
        reference: Component reference designator (e.g., "R1", "C5")
        value: Component value (e.g., "10K", "100nF")
        footprint_name: Footprint/package name (e.g., "C0402", "SOT-23")
        lcsc_number: LCSC part number (e.g., "C60490"), None if not provided
        quantity: Number of this component on the board (default 1)
        status: Processing status
        error_message: Error message if status is ERROR
    """
    reference: str
    value: str
    footprint_name: str
    lcsc_number: Optional[str] = None
    quantity: int = 1
    status: PartStatus = PartStatus.PENDING
    error_message: Optional[str] = None
    
    @property
    def has_lcsc(self) -> bool:
        """Check if this entry has an LCSC number."""
        return bool(self.lcsc_number and self.lcsc_number.strip())
    
    @property
    def part_id(self) -> str:
        """Generate OpenPnP part ID from footprint and value.

        Returns:
            Part ID string (e.g., "C0402-10K" or "C0402-1uF 25v")
        """
        return f"{self.footprint_name}-{self.value}"
    
    @property
    def base_footprint(self) -> str:
        """Extract the base footprint name.
        
        Some BOMs include additional info in footprint name.
        This extracts just the base package type.
        
        Returns:
            Base footprint name (e.g., "C0402" from "C0402_HandSolder")
        """
        # Common suffixes to strip
        suffixes = ["_HandSolder", "_Pad", "_1EP", "_NoVia"]
        name = self.footprint_name
        
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        return name
    
    def set_error(self, message: str) -> None:
        """Set error status with message.
        
        Args:
            message: Error description
        """
        self.status = PartStatus.ERROR
        self.error_message = message
    
    def set_exists(self) -> None:
        """Mark this entry as already existing in OpenPnP."""
        self.status = PartStatus.EXISTS
    
    def set_created(self) -> None:
        """Mark this entry as successfully created."""
        self.status = PartStatus.CREATED
    
    def set_skipped(self) -> None:
        """Mark this entry as skipped by user."""
        self.status = PartStatus.SKIPPED
    
    def set_no_lcsc(self) -> None:
        """Mark this entry as having no LCSC number."""
        self.status = PartStatus.NO_LCSC


@dataclass
class FootprintGroup:
    """Groups BOM entries by shared footprint.
    
    Used to process shared footprints only once.
    
    Attributes:
        footprint_name: The shared footprint name
        entries: BOM entries using this footprint
        lcsc_number: LCSC number to use for fetching (from first entry with one)
        status: Processing status for the group
    """
    footprint_name: str
    entries: list[BomEntry]
    lcsc_number: Optional[str] = None
    status: PartStatus = PartStatus.PENDING
    
    @classmethod
    def from_entries(cls, footprint_name: str, entries: list[BomEntry]) -> "FootprintGroup":
        """Create a FootprintGroup from BOM entries.
        
        Args:
            footprint_name: The shared footprint name
            entries: BOM entries using this footprint
            
        Returns:
            FootprintGroup instance
        """
        # Find the first entry with an LCSC number
        lcsc_number = None
        for entry in entries:
            if entry.has_lcsc:
                lcsc_number = entry.lcsc_number
                break
        
        return cls(
            footprint_name=footprint_name,
            entries=entries,
            lcsc_number=lcsc_number
        )
    
    @property
    def part_count(self) -> int:
        """Number of parts using this footprint."""
        return len(self.entries)
    
    @property
    def has_lcsc(self) -> bool:
        """Check if any entry has an LCSC number."""
        return self.lcsc_number is not None
