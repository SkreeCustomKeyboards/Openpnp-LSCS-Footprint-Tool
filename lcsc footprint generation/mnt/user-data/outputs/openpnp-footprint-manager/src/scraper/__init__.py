"""LCSC/EasyEDA scraping module."""

from .lcsc_client import LCSCClient
from .footprint_parser import FootprintParser

__all__ = ["LCSCClient", "FootprintParser"]
