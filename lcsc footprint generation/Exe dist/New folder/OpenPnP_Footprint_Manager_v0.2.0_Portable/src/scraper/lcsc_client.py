"""LCSC/EasyEDA API client.

Fetches footprint and component data from LCSC/EasyEDA services.

Reference: https://github.com/uPesy/easyeda2kicad.py
"""

import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json


class LCSCApiError(Exception):
    """Error communicating with LCSC API."""
    pass


@dataclass
class EasyEDAComponent:
    """Raw component data from EasyEDA API.
    
    Attributes:
        lcsc_id: LCSC part number (e.g., "C60490")
        title: Component title/description
        footprint_data: Raw footprint JSON data
        symbol_data: Raw symbol JSON data (if available)
    """
    lcsc_id: str
    title: str
    footprint_data: Optional[Dict[str, Any]] = None
    symbol_data: Optional[Dict[str, Any]] = None


class LCSCClient:
    """Client for fetching data from LCSC/EasyEDA APIs.
    
    Uses the EasyEDA API to fetch component footprint data
    based on LCSC part numbers.
    """
    
    # API endpoints (based on easyeda2kicad research)
    EASYEDA_API_BASE = "https://easyeda.com/api"
    LCSC_API_BASE = "https://lcsc.com/api"
    
    def __init__(self, timeout: float = 30.0):
        """Initialize LCSC client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None
    
    def __enter__(self):
        """Context manager entry."""
        self._client = httpx.Client(timeout=self._timeout)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client:
            self._client.close()
            self._client = None
    
    def _ensure_client(self) -> httpx.Client:
        """Ensure HTTP client is initialized.
        
        Returns:
            httpx.Client instance
        """
        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client
    
    def fetch_component(self, lcsc_id: str) -> EasyEDAComponent:
        """Fetch component data from EasyEDA API.

        Args:
            lcsc_id: LCSC part number (e.g., "C60490")

        Returns:
            EasyEDAComponent with fetched data

        Raises:
            LCSCApiError: If fetch fails
        """
        # Clean up LCSC ID
        lcsc_id = lcsc_id.strip().upper()
        if not lcsc_id.startswith("C"):
            lcsc_id = "C" + lcsc_id

        client = self._ensure_client()

        # Fetch component info from EasyEDA
        try:
            # Step 1: Get component info (includes UUID and package UUID)
            url = f"{self.EASYEDA_API_BASE}/products/{lcsc_id}/components"
            response = client.get(url)

            if response.status_code == 404:
                raise LCSCApiError(f"Component not found: {lcsc_id}")

            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                raise LCSCApiError(f"API returned error for {lcsc_id}")

            result = data.get("result")
            if not result:
                raise LCSCApiError(f"No result data for {lcsc_id}")

            component_uuid = result.get("uuid")
            title = result.get("title", f"Component {lcsc_id}")

            if not component_uuid:
                raise LCSCApiError(f"No component UUID for {lcsc_id}")

            # Step 2: Fetch component details to get package UUID
            comp_url = f"{self.EASYEDA_API_BASE}/components/{component_uuid}"
            comp_response = client.get(comp_url)
            comp_response.raise_for_status()
            comp_data = comp_response.json()

            comp_result = comp_data.get("result", {})
            package_detail = comp_result.get("packageDetail")

            if not package_detail:
                raise LCSCApiError(f"No package detail for {lcsc_id}")

            package_uuid = package_detail.get("uuid")
            if not package_uuid:
                raise LCSCApiError(f"No package UUID for {lcsc_id}")

            # Step 3: Fetch actual footprint/package data
            pkg_url = f"{self.EASYEDA_API_BASE}/components/{package_uuid}"
            pkg_response = client.get(pkg_url)
            pkg_response.raise_for_status()
            pkg_data = pkg_response.json()

            footprint_data = pkg_data.get("result")

            return EasyEDAComponent(
                lcsc_id=lcsc_id,
                title=title,
                footprint_data=footprint_data
            )

        except httpx.HTTPError as e:
            raise LCSCApiError(f"HTTP error fetching {lcsc_id}: {e}")
        except json.JSONDecodeError as e:
            raise LCSCApiError(f"Invalid JSON response for {lcsc_id}: {e}")
    
    def _get_component_uuid(self, lcsc_id: str) -> Optional[str]:
        """Get EasyEDA component UUID from LCSC ID.
        
        Args:
            lcsc_id: LCSC part number
            
        Returns:
            Component UUID if found, None otherwise
        """
        client = self._ensure_client()
        
        # EasyEDA API endpoint for component lookup
        # Based on easyeda2kicad reverse engineering
        url = f"{self.EASYEDA_API_BASE}/products/{lcsc_id}/components"
        
        try:
            response = client.get(url)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Extract component UUID from response
            # The exact structure depends on EasyEDA's API
            if isinstance(data, dict) and "result" in data:
                result = data["result"]
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("uuid")
            
            return None
            
        except httpx.HTTPError:
            return None
    
    def _fetch_footprint_data(self, component_uuid: str) -> Optional[Dict[str, Any]]:
        """Fetch footprint data for a component.
        
        Args:
            component_uuid: EasyEDA component UUID
            
        Returns:
            Footprint data dict if found, None otherwise
        """
        client = self._ensure_client()
        
        # EasyEDA API for footprint data
        url = f"{self.EASYEDA_API_BASE}/components/{component_uuid}"
        
        try:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict) and "result" in data:
                return data["result"]
            
            return None
            
        except httpx.HTTPError:
            return None
    
    def check_connection(self) -> bool:
        """Check if API is reachable.
        
        Returns:
            True if API responds, False otherwise
        """
        client = self._ensure_client()
        
        try:
            response = client.get("https://easyeda.com/", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False


# Async version for future GUI integration
class AsyncLCSCClient:
    """Async client for LCSC/EasyEDA APIs.
    
    For use with asyncio in GUI applications.
    """
    
    EASYEDA_API_BASE = "https://easyeda.com/api"
    
    def __init__(self, timeout: float = 30.0):
        """Initialize async client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch_component(self, lcsc_id: str) -> EasyEDAComponent:
        """Async fetch component data.
        
        Args:
            lcsc_id: LCSC part number
            
        Returns:
            EasyEDAComponent with fetched data
            
        Raises:
            LCSCApiError: If fetch fails
        """
        if self._client is None:
            raise LCSCApiError("Client not initialized")
        
        # Implementation similar to sync version
        # but using async/await
        lcsc_id = lcsc_id.strip().upper()
        if not lcsc_id.startswith("C"):
            lcsc_id = "C" + lcsc_id
        
        try:
            # Fetch component info
            url = f"{self.EASYEDA_API_BASE}/products/{lcsc_id}/components"
            response = await self._client.get(url)
            
            if response.status_code == 404:
                raise LCSCApiError(f"Component not found: {lcsc_id}")
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            footprint_data = None
            if isinstance(data, dict) and "result" in data:
                result = data["result"]
                if isinstance(result, list) and len(result) > 0:
                    uuid = result[0].get("uuid")
                    if uuid:
                        # Fetch detailed data
                        detail_url = f"{self.EASYEDA_API_BASE}/components/{uuid}"
                        detail_response = await self._client.get(detail_url)
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            footprint_data = detail_data.get("result")
            
            return EasyEDAComponent(
                lcsc_id=lcsc_id,
                title=f"Component {lcsc_id}",
                footprint_data=footprint_data
            )
            
        except httpx.HTTPError as e:
            raise LCSCApiError(f"HTTP error fetching {lcsc_id}: {e}")
