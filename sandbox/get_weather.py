from __future__ import annotations
import asyncio
import json
import httpx
from app.services.weather_service import resolve_zipcode


async def get_weather(lat: float, lon: float) -> dict:
    """
    Get the weather for a given latitude and longitude.
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": 'temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,weather_code',
        "daily": 'weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,precipitation_sum,precipitation_probability_max',
        "hourly": 'temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,wind_direction_10m',
        "timezone": 'America/Chicago',
        "temperature_unit": 'fahrenheit',
        "wind_speed_unit": 'mph',
        "precipitation_unit": 'inch',
        "timeformat": 'iso8601',
        "forecast_days": 4, # this includes the current day plus 2 days after the current day
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(base_url, params = params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"OpenMeteo API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"OpenMeteo request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format from OpenMeteo API") from e
    
    return data


async def main():
    location = await resolve_zipcode()
    weather = await get_weather(location.lat, location.lon)
    print(weather)

if __name__ == "__main__":
    asyncio.run(main())
