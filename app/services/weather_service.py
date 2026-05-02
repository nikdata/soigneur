"""
This service will fetch the weather data for the hard-code zip code. 

It is focused on retrieving the weather data for the current day along with the forecast for the next 5 days.

The zip code is part of the environment variable LOCATION_ZIP and is "injected" using the Doppler CLI.

"""


from __future__ import annotations
import json
import httpx
from app.config import get_settings
from app.models.geo import GeoLocation


async def resolve_zipcode() -> GeoLocation:
    """
    Resolve the zipcode to a latitude and longitude using the Nominatim API from OpenStreetMap.

    Returns:
        GeoLocation: The latitude and longitude of the zipcode.
    """
    
    # instantiate the settings
    settings = get_settings()
    postal_code = settings.location_zip

    # check to ensure that the postal code is set
    if postal_code is None:
        raise ValueError("LOCATION_ZIP is not set")
    
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
    location = GeoLocation(**data[0])

    return location