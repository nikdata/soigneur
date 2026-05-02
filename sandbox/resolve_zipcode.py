"""
This script will resolve the zipcode to a latitude and longitude.

The zip code is part of the environment variable LOCATION_ZIP and is "injected" using the Doppler CLI.

"""


from __future__ import annotations
import asyncio
import json
import httpx
from app.config import get_settings


async def resolve_zipcode() -> tuple[float, float]:
    """
    Resolve the zipcode to a latitude and longitude using the Nominatim API from OpenStreetMap.

    Returns:
        tuple[float, float]: The latitude and longitude of the zipcode.
    """
    
    # instantiate the settings
    settings = get_settings()
    postal_code = settings.location_zip

    # check to ensure that the postal code is set
    if postal_code is None:
        raise ValueError("LOCATION_ZIP is not set")

    # base_url = f"https://nominatim.openstreetmap.org/search?postalcode={postal_code}&country=United+States&format=json"
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "postalcode": postal_code,
        "country": "United States",
        "format": "json"
    }

    # async client to make the request
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(base_url, params = params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Nominatim API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Nominatim request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format from Nominatim API") from e

    # check to ensure that data is not empty
    if not data:
        raise ValueError(f"No data found for postal code: {postal_code}")
    
    # check to ensure that the data is in the expected format
    payload = data[0]
    
    if "lat" not in payload or "lon" not in payload:
        raise ValueError(f"Unexpected response format for postal code: {postal_code}")

    # convert lat & long to floats
    lat = float(payload["lat"])
    lon = float(payload["lon"])

    gps = (lat, lon)
    return gps

if __name__ == "__main__":
    coord = asyncio.run(resolve_zipcode())
    print("latitude:", coord[0])
    print("longitude:", coord[1])