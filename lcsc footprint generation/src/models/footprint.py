"""Footprint and pad data models.

These models represent the footprint/package data used by OpenPnP.
"""

from dataclasses import dataclass, field
from typing import Optional
from lxml import etree


@dataclass
class Pad:
    """Represents a single pad in a footprint.
    
    Attributes:
        name: Pad identifier (typically "1", "2", etc.)
        x: X position relative to component center (mm)
        y: Y position relative to component center (mm)
        width: Pad width (mm)
        height: Pad height (mm)
        rotation: Pad rotation in degrees (0-360)
        roundness: 0.0 = rectangular, 100.0 = fully circular
    """
    name: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    roundness: float = 0.0
    
    def to_xml_element(self) -> etree._Element:
        """Convert pad to OpenPnP XML element.
        
        Returns:
            lxml Element representing the pad
        """
        return etree.Element(
            "pad",
            name=self.name,
            x=f"{self.x:.4f}",
            y=f"{self.y:.4f}",
            width=f"{self.width:.4f}",
            height=f"{self.height:.4f}",
            rotation=f"{self.rotation:.1f}",
            roundness=f"{self.roundness:.1f}"
        )
    
    @classmethod
    def from_xml_element(cls, element: etree._Element) -> "Pad":
        """Create Pad from OpenPnP XML element.
        
        Args:
            element: lxml Element containing pad data
            
        Returns:
            Pad instance
        """
        return cls(
            name=element.get("name", ""),
            x=float(element.get("x", 0)),
            y=float(element.get("y", 0)),
            width=float(element.get("width", 0)),
            height=float(element.get("height", 0)),
            rotation=float(element.get("rotation", 0)),
            roundness=float(element.get("roundness", 0))
        )


@dataclass
class Footprint:
    """Represents the footprint (pad layout) within a package.
    
    Attributes:
        body_width: Component body width (mm)
        body_height: Component body height (mm)
        pads: List of pads in the footprint
        units: Unit system (always "Millimeters" for OpenPnP)
    """
    body_width: float
    body_height: float
    pads: list[Pad] = field(default_factory=list)
    units: str = "Millimeters"
    
    def to_xml_element(self) -> etree._Element:
        """Convert footprint to OpenPnP XML element.
        
        Returns:
            lxml Element representing the footprint
        """
        footprint_elem = etree.Element(
            "footprint",
            units=self.units,
        )
        footprint_elem.set("body-width", f"{self.body_width:.4f}")
        footprint_elem.set("body-height", f"{self.body_height:.4f}")
        
        for pad in self.pads:
            footprint_elem.append(pad.to_xml_element())
        
        return footprint_elem
    
    @classmethod
    def from_xml_element(cls, element: etree._Element) -> "Footprint":
        """Create Footprint from OpenPnP XML element.
        
        Args:
            element: lxml Element containing footprint data
            
        Returns:
            Footprint instance
        """
        pads = [Pad.from_xml_element(pad_elem) for pad_elem in element.findall("pad")]
        
        return cls(
            body_width=float(element.get("body-width", 0)),
            body_height=float(element.get("body-height", 0)),
            pads=pads,
            units=element.get("units", "Millimeters")
        )
    
    def calculate_bounds(self) -> tuple[float, float, float, float]:
        """Calculate the bounding box of all pads.
        
        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        if not self.pads:
            return (0, 0, 0, 0)
        
        min_x = min(p.x - p.width / 2 for p in self.pads)
        max_x = max(p.x + p.width / 2 for p in self.pads)
        min_y = min(p.y - p.height / 2 for p in self.pads)
        max_y = max(p.y + p.height / 2 for p in self.pads)
        
        return (min_x, min_y, max_x, max_y)


@dataclass
class Package:
    """Represents an OpenPnP package (footprint definition).

    A package is the container for a footprint with additional metadata.

    Attributes:
        id: Unique package identifier (e.g., "R0402", "SOT-23")
        footprint: The footprint containing pads
        description: Optional human-readable description
        version: OpenPnP package version (typically "1.1")
        generator: Tool that generated this package (for tracking)
        import_date: ISO format date of import
        session_id: Unique session identifier for bulk operations
        lcsc_id: LCSC part number used to fetch this footprint
        compatible_nozzle_tip_ids: List of compatible nozzle tip IDs
    """
    id: str
    footprint: Footprint
    description: Optional[str] = None
    version: str = "1.1"
    generator: Optional[str] = None
    import_date: Optional[str] = None
    session_id: Optional[str] = None
    lcsc_id: Optional[str] = None
    compatible_nozzle_tip_ids: list[str] = field(default_factory=list)
    
    def to_xml_element(self) -> etree._Element:
        """Convert package to OpenPnP XML element.

        Returns:
            lxml Element representing the package
        """
        attribs = {
            "version": self.version,
            "id": self.id,
        }
        if self.description:
            attribs["description"] = self.description

        package_elem = etree.Element("package", **attribs)

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
            package_elem.append(comment)

        package_elem.append(self.footprint.to_xml_element())

        # Add compatible nozzle tip IDs
        nozzle_tips_elem = etree.Element("compatible-nozzle-tip-ids")
        nozzle_tips_elem.set("class", "java.util.ArrayList")
        for nozzle_id in self.compatible_nozzle_tip_ids:
            string_elem = etree.Element("string")
            string_elem.text = nozzle_id
            nozzle_tips_elem.append(string_elem)
        package_elem.append(nozzle_tips_elem)

        return package_elem
    
    @classmethod
    def from_xml_element(cls, element: etree._Element) -> "Package":
        """Create Package from OpenPnP XML element.

        Args:
            element: lxml Element containing package data

        Returns:
            Package instance
        """
        footprint_elem = element.find("footprint")
        footprint = Footprint.from_xml_element(footprint_elem) if footprint_elem is not None else Footprint(0, 0)

        return cls(
            id=element.get("id", ""),
            footprint=footprint,
            description=element.get("description"),
            version=element.get("version", "1.1"),
            generator=element.get("x-generator"),
            import_date=element.get("x-import-date"),
            session_id=element.get("x-session-id"),
            lcsc_id=element.get("x-lcsc-id")
        )
    
    def to_xml_string(self, pretty: bool = True) -> str:
        """Convert package to XML string.
        
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
