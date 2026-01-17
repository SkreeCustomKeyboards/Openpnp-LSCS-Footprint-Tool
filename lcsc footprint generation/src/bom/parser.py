"""BOM file parser.

Handles parsing CSV and Excel BOM files into structured data.
"""

from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.part import BomEntry, FootprintGroup


class BomParseError(Exception):
    """Error parsing BOM file."""
    pass


class BomParser:
    """Parser for BOM files in CSV and Excel formats.
    
    Extracts component information including footprint names and
    LCSC part numbers.
    """
    
    # Default column names (can be customized)
    DEFAULT_COLUMNS = {
        "reference": ["Reference", "Ref", "Designator", "RefDes"],
        "value": ["Value", "Val", "Part Value", "Name"],
        "footprint": ["FOOTPRINT-NAME", "Footprint", "Package", "Case"],
        "lcsc": ["supplier part", "LCSC", "LCSC Part", "LCSC#", "MPN", "Manufacturer Part"]
    }
    
    def __init__(self, 
                 footprint_column: Optional[str] = None,
                 lcsc_column: Optional[str] = None,
                 reference_column: Optional[str] = None,
                 value_column: Optional[str] = None):
        """Initialize BOM parser.
        
        Args:
            footprint_column: Custom column name for footprints
            lcsc_column: Custom column name for LCSC numbers
            reference_column: Custom column name for references
            value_column: Custom column name for values
        """
        self._footprint_column = footprint_column
        self._lcsc_column = lcsc_column
        self._reference_column = reference_column
        self._value_column = value_column
    
    def parse(self, filepath: Path) -> List[BomEntry]:
        """Parse a BOM file.
        
        Args:
            filepath: Path to BOM file (CSV or Excel)
            
        Returns:
            List of BomEntry objects
            
        Raises:
            BomParseError: If parsing fails
        """
        if not filepath.exists():
            raise BomParseError(f"File not found: {filepath}")
        
        suffix = filepath.suffix.lower()
        
        try:
            if suffix == ".csv":
                # Try different encodings for CSV files
                encodings = ['utf-16', 'utf-16-le', 'utf-8', 'latin-1']
                df = None
                last_error = None

                for encoding in encodings:
                    try:
                        df = pd.read_csv(filepath, encoding=encoding, sep='\t')
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError) as e:
                        last_error = e
                        continue

                if df is None:
                    raise BomParseError(f"Failed to read CSV with any encoding. Last error: {last_error}")

            elif suffix in (".xlsx", ".xls"):
                df = pd.read_excel(filepath)
            else:
                raise BomParseError(f"Unsupported file format: {suffix}")
        except BomParseError:
            raise
        except Exception as e:
            raise BomParseError(f"Failed to read file: {e}")
        
        return self._parse_dataframe(df)
    
    def _parse_dataframe(self, df: pd.DataFrame) -> List[BomEntry]:
        """Parse a pandas DataFrame into BOM entries.
        
        Args:
            df: DataFrame with BOM data
            
        Returns:
            List of BomEntry objects
        """
        # Find column mappings
        columns = self._find_columns(df.columns.tolist())
        
        if not columns.get("footprint"):
            raise BomParseError(
                "Could not find footprint column. "
                f"Expected one of: {self.DEFAULT_COLUMNS['footprint']}"
            )
        
        entries = []
        
        for idx, row in df.iterrows():
            try:
                entry = self._parse_row(row, columns)
                if entry:
                    entries.append(entry)
            except (KeyError, ValueError):
                continue
        
        return entries
    
    def _find_columns(self, column_names: List[str]) -> Dict[str, Optional[str]]:
        """Find the actual column names in the DataFrame.
        
        Args:
            column_names: List of column names from DataFrame
            
        Returns:
            Dict mapping field names to actual column names
        """
        result = {}
        
        # Check for custom columns first
        custom_mappings = {
            "reference": self._reference_column,
            "value": self._value_column,
            "footprint": self._footprint_column,
            "lcsc": self._lcsc_column
        }
        
        for field, custom_col in custom_mappings.items():
            if custom_col and custom_col in column_names:
                result[field] = custom_col
                continue
            
            # Search for default column names (case-insensitive)
            found = None
            for default_name in self.DEFAULT_COLUMNS[field]:
                for col_name in column_names:
                    if col_name.lower() == default_name.lower():
                        found = col_name
                        break
                if found:
                    break
            
            result[field] = found
        
        return result
    
    def _parse_row(self, row: pd.Series, columns: Dict[str, Optional[str]]) -> Optional[BomEntry]:
        """Parse a single row into a BomEntry.
        
        Args:
            row: DataFrame row
            columns: Column name mapping
            
        Returns:
            BomEntry or None if row is invalid
        """
        # Get footprint (required)
        footprint_col = columns.get("footprint")
        if not footprint_col:
            return None
        
        footprint = str(row.get(footprint_col, "")).strip()
        if not footprint or footprint.lower() == "nan":
            return None
        
        # Get reference
        reference_col = columns.get("reference")
        reference = ""
        if reference_col:
            ref_val = row.get(reference_col, "")
            reference = str(ref_val).strip() if pd.notna(ref_val) else ""
        
        # Get value
        value_col = columns.get("value")
        value = ""
        if value_col:
            val_val = row.get(value_col, "")
            value = str(val_val).strip() if pd.notna(val_val) else ""
        
        # Get LCSC number (optional)
        lcsc_col = columns.get("lcsc")
        lcsc_number = None
        if lcsc_col:
            lcsc_val = row.get(lcsc_col, "")
            if pd.notna(lcsc_val):
                lcsc_str = str(lcsc_val).strip()
                if lcsc_str and lcsc_str.lower() != "nan":
                    lcsc_number = lcsc_str
        
        return BomEntry(
            reference=reference,
            value=value,
            footprint_name=footprint,
            lcsc_number=lcsc_number
        )
    
    def group_by_footprint(self, entries: List[BomEntry]) -> List[FootprintGroup]:
        """Group BOM entries by footprint name.
        
        Combines entries that share the same base footprint.
        
        Args:
            entries: List of BOM entries
            
        Returns:
            List of FootprintGroup objects
        """
        # Group by base footprint name
        groups: Dict[str, List[BomEntry]] = {}
        
        for entry in entries:
            base = entry.base_footprint
            if base not in groups:
                groups[base] = []
            groups[base].append(entry)
        
        # Create FootprintGroup objects
        result = []
        for footprint_name, group_entries in groups.items():
            group = FootprintGroup.from_entries(footprint_name, group_entries)
            result.append(group)
        
        # Sort by footprint name
        result.sort(key=lambda g: g.footprint_name)
        
        return result


def parse_bom(filepath: Path) -> List[BomEntry]:
    """Convenience function to parse a BOM file.
    
    Args:
        filepath: Path to BOM file
        
    Returns:
        List of BomEntry objects
    """
    parser = BomParser()
    return parser.parse(filepath)


def get_unique_footprints(entries: List[BomEntry]) -> List[str]:
    """Get list of unique footprint names from BOM entries.
    
    Args:
        entries: List of BOM entries
        
    Returns:
        Sorted list of unique footprint names
    """
    footprints = set()
    for entry in entries:
        footprints.add(entry.base_footprint)
    return sorted(footprints)


def filter_entries_with_lcsc(entries: List[BomEntry]) -> List[BomEntry]:
    """Filter entries to only those with LCSC numbers.
    
    Args:
        entries: List of BOM entries
        
    Returns:
        Entries that have LCSC numbers
    """
    return [e for e in entries if e.has_lcsc]


def filter_entries_without_lcsc(entries: List[BomEntry]) -> List[BomEntry]:
    """Filter entries to only those without LCSC numbers.
    
    Args:
        entries: List of BOM entries
        
    Returns:
        Entries that lack LCSC numbers
    """
    return [e for e in entries if not e.has_lcsc]
