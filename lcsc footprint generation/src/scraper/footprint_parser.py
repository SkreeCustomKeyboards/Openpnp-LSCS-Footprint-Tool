"""Parser for converting EasyEDA footprint data to OpenPnP format.

Handles the conversion from EasyEDA's JSON format to OpenPnP's XML structures.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.footprint import Pad, Footprint, Package


class FootprintParseError(Exception):
    """Error parsing footprint data."""
    pass


@dataclass
class EasyEDAPad:
    """Raw pad data from EasyEDA format.
    
    EasyEDA uses different units and coordinate systems.
    """
    number: str
    shape: str  # "RECT", "OVAL", "ELLIPSE", "ROUND"
    x: float  # in EasyEDA units (10 units = 1 mil)
    y: float
    width: float
    height: float
    rotation: float
    hole_radius: float = 0.0  # For through-hole pads


class FootprintParser:
    """Converts EasyEDA footprint data to OpenPnP format.
    
    EasyEDA uses a coordinate system where:
    - 10 units = 1 mil
    - Y axis may be inverted
    - Origin is typically at component center
    """
    
    # Conversion factor: EasyEDA units to mm
    # 1 EasyEDA unit = 10 mils = 0.254 mm
    UNITS_TO_MM = 0.254
    
    def __init__(self):
        """Initialize parser."""
        pass
    
    def parse(self, data: Dict[str, Any], package_id: str, lcsc_id: Optional[str] = None,
              session_id: Optional[str] = None) -> Package:
        """Parse EasyEDA data into an OpenPnP Package.

        Args:
            data: Raw EasyEDA component data
            package_id: ID to use for the package
            lcsc_id: LCSC part number (for metadata tracking)
            session_id: Import session ID (for bulk removal)

        Returns:
            OpenPnP Package object

        Raises:
            FootprintParseError: If parsing fails
        """
        if not data:
            raise FootprintParseError("Empty footprint data")
        
        # EasyEDA data structure varies, try different paths
        pads_data = self._extract_pads_data(data)
        
        if not pads_data:
            raise FootprintParseError("No pad data found")
        
        # Parse all pads
        pads = []
        for pad_key, pad_data in pads_data.items():
            try:
                pad = self._parse_pad(pad_key, pad_data)
                if pad:
                    pads.append(pad)
            except (KeyError, ValueError) as e:
                # Skip malformed pads
                continue
        
        if not pads:
            raise FootprintParseError("No valid pads found")
        
        # Convert to mm coordinates
        mm_pads = [self._convert_pad_to_mm(p) for p in pads]
        
        # Calculate body dimensions from pad extents
        body_width, body_height = self._calculate_body_size(mm_pads)
        
        # Center the footprint
        mm_pads = self._center_footprint(mm_pads)
        
        # Create OpenPnP footprint
        footprint = Footprint(
            body_width=body_width,
            body_height=body_height,
            pads=mm_pads
        )
        
        # Determine description
        description = self._generate_description(mm_pads)

        # Get current timestamp
        from datetime import datetime
        import_date = datetime.now().isoformat()

        return Package(
            id=package_id,
            footprint=footprint,
            description=description,
            generator="OpenPnP-Footprint-Manager",
            import_date=import_date,
            session_id=session_id,
            lcsc_id=lcsc_id
        )
    
    def _extract_pads_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pad data from various EasyEDA response formats.

        Args:
            data: Raw EasyEDA data

        Returns:
            Dict of pad data
        """
        # Try different possible locations for pad data
        # EasyEDA format varies between versions

        # Format 1: Shape array (current EasyEDA API format)
        # dataStr.shape contains array of strings like "PAD~RECT~x~y~w~h..."
        if "dataStr" in data:
            datastr = data["dataStr"]
            if isinstance(datastr, dict) and "shape" in datastr:
                shapes = datastr["shape"]
                if isinstance(shapes, list):
                    # Parse PAD strings
                    pads_dict = {}
                    for shape_str in shapes:
                        if isinstance(shape_str, str) and shape_str.startswith("PAD~"):
                            pad = self._parse_pad_string(shape_str)
                            if pad:
                                pads_dict[pad.number] = pad
                    if pads_dict:
                        # Convert EasyEDAPad objects to dicts for compatibility
                        return {k: self._easyeda_pad_to_dict(v) for k, v in pads_dict.items()}

        # Format 2: Direct PAD key
        if "PAD" in data:
            return data["PAD"]

        # Format 3: Nested in dataStr (JSON string)
        if "dataStr" in data:
            import json
            try:
                inner = json.loads(data["dataStr"])
                if "PAD" in inner:
                    return inner["PAD"]
            except (json.JSONDecodeError, TypeError):
                pass

        # Format 4: In footprint object
        if "footprint" in data:
            fp = data["footprint"]
            if isinstance(fp, dict) and "PAD" in fp:
                return fp["PAD"]

        # Format 5: Direct pad list
        if "pads" in data:
            # Convert list to dict
            pads_dict = {}
            for i, pad in enumerate(data["pads"]):
                pads_dict[str(i)] = pad
            return pads_dict

        return {}

    def _parse_pad_string(self, pad_str: str) -> Optional[EasyEDAPad]:
        """Parse EasyEDA PAD string format.

        Format: PAD~RECT~x~y~width~height~layer~~number~0~coords~rotation~...
        Index:   0   1    2  3    4       5      6   7   8    9   10      11

        Args:
            pad_str: PAD string from shape array

        Returns:
            EasyEDAPad object or None if invalid
        """
        parts = pad_str.split("~")
        if len(parts) < 12:  # Need at least 12 parts to get rotation
            return None

        try:
            shape = parts[1]  # RECT, OVAL, ELLIPSE, ROUND
            x = float(parts[2])
            y = float(parts[3])
            width = float(parts[4])
            height = float(parts[5])
            # parts[6] is layer
            # parts[7] is usually empty
            number = parts[8] if parts[8] else "1"
            # parts[9] is usually "0"
            # parts[10] is coordinate list (polygon points)
            rotation = float(parts[11]) if len(parts) > 11 and parts[11] else 0.0

            return EasyEDAPad(
                number=str(number),
                shape=shape,
                x=x,
                y=y,
                width=width,
                height=height,
                rotation=rotation,
                hole_radius=0.0
            )
        except (ValueError, IndexError):
            return None

    def _easyeda_pad_to_dict(self, pad: EasyEDAPad) -> Dict[str, Any]:
        """Convert EasyEDAPad to dict format for compatibility.

        Args:
            pad: EasyEDAPad object

        Returns:
            Dict representation
        """
        return {
            "number": pad.number,
            "shape": pad.shape,
            "x": pad.x,
            "y": pad.y,
            "width": pad.width,
            "height": pad.height,
            "rotation": pad.rotation,
            "holeR": pad.hole_radius
        }
    
    def _parse_pad(self, pad_key: str, pad_data: Dict[str, Any]) -> Optional[EasyEDAPad]:
        """Parse a single pad from EasyEDA data.
        
        Args:
            pad_key: Pad identifier key
            pad_data: Pad data dict
            
        Returns:
            EasyEDAPad object or None if invalid
        """
        # Get pad number/name
        number = pad_data.get("number", pad_data.get("name", pad_key))
        
        # Get shape
        shape = pad_data.get("shape", "RECT")
        if isinstance(shape, int):
            # EasyEDA sometimes uses numeric shape codes
            shape_map = {1: "RECT", 2: "ROUND", 3: "OVAL", 4: "ELLIPSE"}
            shape = shape_map.get(shape, "RECT")
        
        # Get coordinates
        try:
            x = float(pad_data.get("x", 0))
            y = float(pad_data.get("y", 0))
            width = float(pad_data.get("width", 0))
            height = float(pad_data.get("height", width))  # Default to square
            rotation = float(pad_data.get("rotation", 0))
            hole_radius = float(pad_data.get("holeR", 0))
        except (ValueError, TypeError):
            return None
        
        # Skip invalid pads
        if width <= 0 or height <= 0:
            return None
        
        return EasyEDAPad(
            number=str(number),
            shape=shape.upper() if isinstance(shape, str) else "RECT",
            x=x,
            y=y,
            width=width,
            height=height,
            rotation=rotation,
            hole_radius=hole_radius
        )
    
    def _convert_pad_to_mm(self, eda_pad: EasyEDAPad) -> Pad:
        """Convert EasyEDA pad to OpenPnP pad in mm.

        Args:
            eda_pad: EasyEDA pad data

        Returns:
            OpenPnP Pad in millimeters
        """
        # Convert coordinates
        x_mm = eda_pad.x * self.UNITS_TO_MM
        # IMPORTANT: Invert Y-axis to match OpenPnP coordinate system
        # EasyEDA uses bottom-left origin with Y increasing upward
        # OpenPnP uses center origin with Y increasing downward
        # The inversion happens here, centering happens later
        y_mm = -eda_pad.y * self.UNITS_TO_MM
        width_mm = eda_pad.width * self.UNITS_TO_MM
        height_mm = eda_pad.height * self.UNITS_TO_MM

        # Determine roundness from shape
        # 100 = fully round (circle), 50 = oval, 0 = rectangular
        if eda_pad.shape in ("ROUND", "CIRCLE"):
            roundness = 100.0
        elif eda_pad.shape == "OVAL":
            roundness = 50.0
        else:  # RECT
            roundness = 0.0

        return Pad(
            name=eda_pad.number,
            x=x_mm,
            y=y_mm,
            width=width_mm,
            height=height_mm,
            rotation=eda_pad.rotation,
            roundness=roundness
        )
    
    def _calculate_body_size(self, pads: List[Pad]) -> tuple[float, float]:
        """Calculate component body size from pad positions.
        
        The body is estimated as slightly larger than pad extents.
        
        Args:
            pads: List of pads in mm
            
        Returns:
            Tuple of (body_width, body_height) in mm
        """
        if not pads:
            return (1.0, 1.0)
        
        # Find pad extents
        min_x = min(p.x - p.width / 2 for p in pads)
        max_x = max(p.x + p.width / 2 for p in pads)
        min_y = min(p.y - p.height / 2 for p in pads)
        max_y = max(p.y + p.height / 2 for p in pads)
        
        # Body size with small margin
        width = max_x - min_x
        height = max_y - min_y
        
        # For 2-pad components (like 0402), use standard body dimensions
        if len(pads) == 2:
            # Estimate body from pad spacing
            # Pads are typically at edges, body is between
            width = abs(pads[0].x - pads[1].x)
            height = max(p.height for p in pads)
        
        return (max(width, 0.1), max(height, 0.1))
    
    def _center_footprint(self, pads: List[Pad]) -> List[Pad]:
        """Center footprint so origin is at component center.
        
        Args:
            pads: List of pads
            
        Returns:
            New list with centered pads
        """
        if not pads:
            return pads
        
        # Find center of all pads
        center_x = sum(p.x for p in pads) / len(pads)
        center_y = sum(p.y for p in pads) / len(pads)
        
        # Create new centered pads
        centered = []
        for p in pads:
            centered.append(Pad(
                name=p.name,
                x=p.x - center_x,
                y=p.y - center_y,
                width=p.width,
                height=p.height,
                rotation=p.rotation,
                roundness=p.roundness
            ))
        
        return centered
    
    def _generate_description(self, pads: List[Pad]) -> str:
        """Generate description for the package.
        
        Args:
            pads: List of pads
            
        Returns:
            Description string
        """
        pad_count = len(pads)
        
        if pad_count == 2:
            return f"2-pad SMD component"
        elif pad_count == 3:
            return f"3-pin component (SOT-23 style)"
        elif pad_count <= 8:
            return f"{pad_count}-pin SMD component"
        else:
            return f"{pad_count}-pin IC"


def parse_easyeda_response(data: Dict[str, Any], package_id: str) -> Package:
    """Convenience function to parse EasyEDA response.
    
    Args:
        data: Raw API response data
        package_id: ID for the package
        
    Returns:
        OpenPnP Package
    """
    parser = FootprintParser()
    return parser.parse(data, package_id)
