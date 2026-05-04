"""
This service will fetch the weather data for the hard-code zip code.

It is focused on retrieving the weather data for the current day along with the forecast for the current day plus the next 3 days.

The zip code is part of the environment variable LOCATION_ZIP and is "injected" using the Doppler CLI.

"""

from __future__ import annotations
import json
import httpx
from datetime import datetime, date
from app.config import get_settings
from app.models.geo import GeoLocation
from app.models.weather import (
    WeatherForecast,
    CurrentWeather,
    DailyWeather,
    HourlyWeather,
)


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
    params = {"postalcode": postal_code, "country": "United States", "format": "json"}

    # async client to make the request
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(base_url, params=params)
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


def parse_weather_forecast(payload: dict) -> WeatherForecast:
    """
    Map a decoded Open-Meteo ``/v1/forecast`` JSON body to :class:`WeatherForecast`.
    Args:
        payload: Raw JSON object (dict) from Open-Meteo.
    Returns:
        Structured forecast.
    Raises:
        KeyError: If required sections or variables are missing.
        ValueError: If time strings cannot be parsed or array lengths disagree.
    """
    # parse the current weather
    cur = payload["current"]
    current = CurrentWeather(
        datetime=datetime.fromisoformat(cur["time"]),
        temperature=float(cur["temperature_2m"]),
        relative_humidity=float(cur["relative_humidity_2m"]),
        weather_code=int(cur["weather_code"]),
        wind_speed=float(cur["wind_speed_10m"]),
        wind_direction=int(cur["wind_direction_10m"]),
        wind_gusts=float(cur["wind_gusts_10m"]),
        precipitation=float(cur["precipitation"]),
    )
    # parse the daily forecast
    d = payload["daily"]
    daily_times = d["time"]
    n_daily = len(daily_times)
    expected_keys_daily = (
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
        "wind_direction_10m_dominant",
        "precipitation_sum",
        "precipitation_probability_max",
    )
    daily_list: list[DailyWeather] = []
    for key in expected_keys_daily:
        if len(d[key]) != n_daily:
            raise ValueError(
                f"Daily length mismatch for {key}: {len(d[key])} != {n_daily}"
            )
    for i in range(n_daily):
        daily_list.append(
            DailyWeather(
                date=date.fromisoformat(daily_times[i]),
                weather_code=int(d["weather_code"][i]),
                temperature_max=float(d["temperature_2m_max"][i]),
                temperature_min=float(d["temperature_2m_min"][i]),
                wind_speed_max=float(d["wind_speed_10m_max"][i]),
                wind_gusts_max=float(d["wind_gusts_10m_max"][i]),
                wind_direction_dominant=int(d["wind_direction_10m_dominant"][i]),
                precipitation_sum=float(d["precipitation_sum"][i]),
                precipitation_probability_max=int(
                    d["precipitation_probability_max"][i]
                ),
            )
        )
    # parse the hourly forecast
    h = payload["hourly"]
    hourly_times = h["time"]
    n_hourly = len(hourly_times)
    expected_keys = (
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation_probability",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
    )
    for key in expected_keys:
        if len(h[key]) != n_hourly:
            raise ValueError(
                f"Hourly length mismatch for {key}: {len(h[key])} != {n_hourly}"
            )
    hourly_list: list[HourlyWeather] = []
    for i in range(n_hourly):
        hourly_list.append(
            HourlyWeather(
                datetime=datetime.fromisoformat(hourly_times[i]),
                temperature=float(h["temperature_2m"][i]),
                relative_humidity=float(h["relative_humidity_2m"][i]),
                precipitation_probability=int(h["precipitation_probability"][i]),
                precipitation=float(h["precipitation"][i]),
                weather_code=int(h["weather_code"][i]),
                wind_speed=float(h["wind_speed_10m"][i]),
                wind_gusts=float(h["wind_gusts_10m"][i]),
                wind_direction=int(h["wind_direction_10m"][i]),
            )
        )
    return WeatherForecast(current=current, daily=daily_list, hourly=hourly_list)


async def fetch_weather_forecast(lat: float, lon: float) -> WeatherForecast:
    """
    Get the weather for a given latitude and longitude.

    Args:
        lat: The latitude of the location
        lon: The longitude of the location

    Returns:
        WeatherForecast: The weather forecast data
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,precipitation_sum,precipitation_probability_max",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "timezone": "America/Chicago",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timeformat": "iso8601",
        "forecast_days": 4,  # this includes the current day plus 3 days after the current day
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"OpenMeteo API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"OpenMeteo request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format from OpenMeteo API") from e

    return parse_weather_forecast(data)
