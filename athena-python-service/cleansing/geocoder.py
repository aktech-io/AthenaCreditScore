from __future__ import annotations

import time
from typing import Optional, Dict, Any

import requests
import structlog

logger = structlog.get_logger(__name__)

_NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
_REQUEST_DELAY = 1.1  # Nominatim rate limit: max 1 req/sec


class Geocoder:
    """
    Resolves lat/long coordinates to standardized Kenyan admin levels
    via OpenStreetMap Nominatim (free, no API key needed).

    Returns: county, sub_county, ward, display_name
    Batches are rate-limited to respect Nominatim's 1 req/s limit.
    """

    def __init__(
        self,
        base_url: str = _NOMINATIM_BASE,
        user_agent: str = "AthenaCreditScore/2.0 (contact@athena.co.ke)",
    ):
        self.base_url = base_url
        self.headers = {"User-Agent": user_agent}

    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Optional[str]]:
        """
        Reverse geocode a lat/lon pair to admin level fields.
        Returns a dict with: county, sub_county, ward, display_name.
        """
        url = f"{self.base_url}/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 14,  # neighbourhood level
            "addressdetails": 1,
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            address = data.get("address", {})
            return {
                "county": address.get("county") or address.get("state_district"),
                "sub_county": address.get("city") or address.get("town") or address.get("village"),
                "ward": address.get("suburb") or address.get("neighbourhood"),
                "display_name": data.get("display_name"),
                "lat": lat,
                "lon": lon,
            }
        except Exception as exc:
            logger.warning("Geocoding failed", lat=lat, lon=lon, error=str(exc))
            return {"county": None, "sub_county": None, "ward": None, "display_name": None}

    def geocode_address(self, address: str, country: str = "Kenya") -> Dict[str, Any]:
        """
        Forward geocode: address string → lat/lon + admin levels.
        """
        url = f"{self.base_url}/search"
        params = {
            "q": f"{address}, {country}",
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            results = resp.json()
            if not results:
                return {"lat": None, "lon": None, "county": None, "sub_county": None, "ward": None}
            r = results[0]
            lat = float(r["lat"])
            lon = float(r["lon"])
            time.sleep(_REQUEST_DELAY)  # Respect rate limit before next call
            return self.reverse_geocode(lat, lon)
        except Exception as exc:
            logger.warning("Forward geocoding failed", address=address, error=str(exc))
            return {"lat": None, "lon": None, "county": None, "sub_county": None, "ward": None}

    def batch_reverse_geocode(
        self, coordinates: list[tuple[float, float]]
    ) -> list[Dict[str, Optional[str]]]:
        """
        Batch reverse geocode a list of (lat, lon) tuples.
        Automatically rate-limited to 1 req/sec.
        """
        results = []
        for i, (lat, lon) in enumerate(coordinates):
            result = self.reverse_geocode(lat, lon)
            results.append(result)
            if i < len(coordinates) - 1:
                time.sleep(_REQUEST_DELAY)
        return results
