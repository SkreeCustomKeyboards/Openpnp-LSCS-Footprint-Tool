"""Tests for data models."""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.footprint import Pad, Footprint, Package
from models.part import Part, BomEntry, PartStatus, FootprintGroup


class TestPad:
    """Tests for Pad model."""
    
    def test_pad_creation(self):
        """Test basic pad creation."""
        pad = Pad(
            name="1",
            x=-0.5,
            y=0.0,
            width=0.5,
            height=0.6
        )
        assert pad.name == "1"
        assert pad.x == -0.5
        assert pad.rotation == 0.0  # Default
        assert pad.roundness == 0.0  # Default
    
    def test_pad_to_xml(self):
        """Test pad XML conversion."""
        pad = Pad(
            name="1",
            x=-0.5,
            y=0.0,
            width=0.5,
            height=0.6,
            rotation=90.0,
            roundness=50.0
        )
        elem = pad.to_xml_element()
        
        assert elem.tag == "pad"
        assert elem.get("name") == "1"
        assert elem.get("x") == "-0.5000"
        assert elem.get("rotation") == "90.0"
    
    def test_pad_from_xml(self):
        """Test pad parsing from XML."""
        from lxml import etree
        
        xml_str = '<pad name="2" x="0.5" y="0.0" width="0.5" height="0.6" rotation="0.0" roundness="100.0"/>'
        elem = etree.fromstring(xml_str)
        
        pad = Pad.from_xml_element(elem)
        
        assert pad.name == "2"
        assert pad.x == 0.5
        assert pad.roundness == 100.0


class TestFootprint:
    """Tests for Footprint model."""
    
    def test_footprint_creation(self):
        """Test footprint creation with pads."""
        pads = [
            Pad(name="1", x=-0.5, y=0.0, width=0.5, height=0.6),
            Pad(name="2", x=0.5, y=0.0, width=0.5, height=0.6)
        ]
        footprint = Footprint(
            body_width=1.0,
            body_height=0.5,
            pads=pads
        )
        
        assert footprint.body_width == 1.0
        assert len(footprint.pads) == 2
        assert footprint.units == "Millimeters"
    
    def test_calculate_bounds(self):
        """Test footprint bounds calculation."""
        pads = [
            Pad(name="1", x=-1.0, y=-0.5, width=0.5, height=0.5),
            Pad(name="2", x=1.0, y=0.5, width=0.5, height=0.5)
        ]
        footprint = Footprint(
            body_width=2.0,
            body_height=1.0,
            pads=pads
        )
        
        min_x, min_y, max_x, max_y = footprint.calculate_bounds()
        
        assert min_x == -1.25  # -1.0 - 0.5/2
        assert max_x == 1.25   # 1.0 + 0.5/2


class TestPackage:
    """Tests for Package model."""
    
    def test_package_creation(self):
        """Test package creation."""
        footprint = Footprint(body_width=1.0, body_height=0.5, pads=[])
        package = Package(
            id="R0402",
            footprint=footprint,
            description="Resistor R0402"
        )
        
        assert package.id == "R0402"
        assert package.version == "1.1"
    
    def test_package_to_xml_string(self):
        """Test package XML string generation."""
        footprint = Footprint(
            body_width=1.0,
            body_height=0.5,
            pads=[
                Pad(name="1", x=-0.5, y=0.0, width=0.5, height=0.6),
                Pad(name="2", x=0.5, y=0.0, width=0.5, height=0.6)
            ]
        )
        package = Package(
            id="R0402",
            footprint=footprint,
            description="Test"
        )
        
        xml_str = package.to_xml_string()
        
        assert '<package version="1.1" id="R0402"' in xml_str
        assert '<pad name="1"' in xml_str


class TestPart:
    """Tests for Part model."""
    
    def test_part_creation(self):
        """Test part creation."""
        part = Part(
            id="R0402-10K",
            package_id="R0402",
            height=0.5
        )
        
        assert part.id == "R0402-10K"
        assert part.speed == 1.0  # Default
    
    def test_part_to_xml(self):
        """Test part XML conversion."""
        part = Part(
            id="R0402-10K",
            package_id="R0402",
            height=0.5,
            speed=0.8
        )
        
        elem = part.to_xml_element()
        
        assert elem.tag == "part"
        assert elem.get("id") == "R0402-10K"
        assert elem.get("package-id") == "R0402"


class TestBomEntry:
    """Tests for BomEntry model."""
    
    def test_bom_entry_creation(self):
        """Test BOM entry creation."""
        entry = BomEntry(
            reference="R1",
            value="10K",
            footprint_name="C0402",
            lcsc_number="C60490"
        )
        
        assert entry.reference == "R1"
        assert entry.has_lcsc is True
        assert entry.status == PartStatus.PENDING
    
    def test_part_id_generation(self):
        """Test part ID generation."""
        entry = BomEntry(
            reference="R1",
            value="10K",
            footprint_name="C0402"
        )
        
        assert entry.part_id == "C0402-10K"
    
    def test_base_footprint_extraction(self):
        """Test base footprint name extraction."""
        # Test normal name
        entry1 = BomEntry(
            reference="R1",
            value="10K",
            footprint_name="C0402"
        )
        assert entry1.base_footprint == "C0402"
        
        # Test with suffix
        entry2 = BomEntry(
            reference="R2",
            value="10K",
            footprint_name="C0402_HandSolder"
        )
        assert entry2.base_footprint == "C0402"
    
    def test_status_changes(self):
        """Test status change methods."""
        entry = BomEntry(
            reference="R1",
            value="10K",
            footprint_name="C0402"
        )
        
        entry.set_exists()
        assert entry.status == PartStatus.EXISTS
        
        entry.set_error("Test error")
        assert entry.status == PartStatus.ERROR
        assert entry.error_message == "Test error"


class TestFootprintGroup:
    """Tests for FootprintGroup model."""
    
    def test_group_creation(self):
        """Test footprint group creation."""
        entries = [
            BomEntry("R1", "10K", "C0402", "C60490"),
            BomEntry("R2", "10K", "C0402", "C60490"),
            BomEntry("R3", "20K", "C0402", None),  # No LCSC
        ]
        
        group = FootprintGroup.from_entries("C0402", entries)
        
        assert group.footprint_name == "C0402"
        assert group.part_count == 3
        assert group.lcsc_number == "C60490"  # From first entry with LCSC
        assert group.has_lcsc is True
    
    def test_group_without_lcsc(self):
        """Test group with no LCSC numbers."""
        entries = [
            BomEntry("R1", "10K", "CUSTOM_FP", None),
        ]
        
        group = FootprintGroup.from_entries("CUSTOM_FP", entries)
        
        assert group.has_lcsc is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
