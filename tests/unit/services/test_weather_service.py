"""Unit tests for app.services.weather_service."""

from __future__ import annotations
import pytest
import httpx
from datetime import datetime, date
from unittest.mock import AsyncMock, patch

from app.services.weather_service import (
    resolve_zipcode,
    parse_weather_forecast,
    fetch_weather_forecast,
)
from app.models.geo import GeoLocation
from app.models.weather import WeatherForecast


NOMINATIM_RESPONSE = [{"lat": 30.2672, "lon": -97.7431}]
NOMINATIM_REQUEST = httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
OPEN_METEO_REQUEST = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")

OPEN_METEO_PAYLOAD = {
    "current": {
        "time": "2026-05-03T12:00",
        "temperature_2m": 85.0,
        "relative_humidity_2m": 55.0,
        "weather_code": 0,
        "wind_speed_10m": 8.5,
        "wind_direction_10m": 180,
        "wind_gusts_10m": 15.0,
        "precipitation": 0.0,
    },
    "daily": {
        "time": ["2026-05-03", "2026-05-04"],
        "weather_code": [0, 3],
        "temperature_2m_max": [90.0, 88.0],
        "temperature_2m_min": [68.0, 65.0],
        "wind_speed_10m_max": [12.0, 10.0],
        "wind_gusts_10m_max": [20.0, 18.0],
        "wind_direction_10m_dominant": [180, 200],
        "precipitation_sum": [0.0, 0.1],
        "precipitation_probability_max": [5, 30],
    },
    "hourly": {
        "time": ["2026-05-03T12:00", "2026-05-03T13:00"],
        "temperature_2m": [85.0, 86.0],
        "relative_humidity_2m": [55.0, 53.0],
        "precipitation_probability": [5, 10],
        "precipitation": [0.0, 0.0],
        "weather_code": [0, 1],
        "wind_speed_10m": [8.5, 9.0],
        "wind_gusts_10m": [15.0, 16.0],
        "wind_direction_10m": [180, 185],
    },
}


# --- resolve_zipcode ---


async def test_resolve_zipcode_success_returns_geo_location(monkeypatch):
    """Verify that a valid Nominatim response is parsed into a GeoLocation."""
    monkeypatch.setenv("LOCATION_ZIP", "78701")

    mock_response = httpx.Response(200, json=NOMINATIM_RESPONSE, request=NOMINATIM_REQUEST)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        location = await resolve_zipcode()

    assert isinstance(location, GeoLocation)
    assert location.lat == pytest.approx(30.2672)
    assert location.lon == pytest.approx(-97.7431)


async def test_resolve_zipcode_missing_env_raises_value_error(monkeypatch):
    """Verify that a missing LOCATION_ZIP raises ValueError."""
    monkeypatch.delenv("LOCATION_ZIP", raising=False)

    with pytest.raises(ValueError, match="LOCATION_ZIP is not set"):
        await resolve_zipcode()


async def test_resolve_zipcode_empty_response_raises_value_error(monkeypatch):
    """Verify that an empty Nominatim response raises ValueError."""
    monkeypatch.setenv("LOCATION_ZIP", "00000")

    mock_response = httpx.Response(200, json=[], request=NOMINATIM_REQUEST)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="No data found"):
            await resolve_zipcode()


async def test_resolve_zipcode_http_status_error_raises_runtime_error(monkeypatch):
    """Verify that an HTTP error from Nominatim raises RuntimeError."""
    monkeypatch.setenv("LOCATION_ZIP", "78701")

    request = httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=request,
            response=httpx.Response(500, request=request),
        )
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Nominatim API error: 500"):
            await resolve_zipcode()


async def test_resolve_zipcode_request_error_raises_runtime_error(monkeypatch):
    """Verify that a network-level failure raises RuntimeError."""
    monkeypatch.setenv("LOCATION_ZIP", "78701")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx.RequestError("Connection refused")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Nominatim request failed"):
            await resolve_zipcode()


# --- parse_weather_forecast ---


def test_parse_weather_forecast_success_builds_models():
    """Verify that a valid Open-Meteo payload is parsed into a WeatherForecast."""
    forecast = parse_weather_forecast(OPEN_METEO_PAYLOAD)

    assert isinstance(forecast, WeatherForecast)
    assert forecast.current.temperature == pytest.approx(85.0)
    assert forecast.current.weather_code == 0
    assert forecast.current.description == "Clear sky"
    assert len(forecast.daily) == 2
    assert forecast.daily[0].date == date(2026, 5, 3)
    assert forecast.daily[1].temperature_max == pytest.approx(88.0)
    assert len(forecast.hourly) == 2
    assert forecast.hourly[0].datetime == datetime(2026, 5, 3, 12, 0)


def test_parse_weather_forecast_hourly_length_mismatch_raises_value_error():
    """Verify that mismatched hourly array lengths raise ValueError."""
    payload = {
        **OPEN_METEO_PAYLOAD,
        "hourly": {
            **OPEN_METEO_PAYLOAD["hourly"],
            "temperature_2m": [85.0],
        },
    }

    with pytest.raises(ValueError, match="Hourly length mismatch"):
        parse_weather_forecast(payload)


def test_parse_weather_forecast_daily_length_mismatch_raises_value_error():
    """Verify that mismatched daily array lengths raise ValueError."""
    payload = {
        **OPEN_METEO_PAYLOAD,
        "daily": {
            **OPEN_METEO_PAYLOAD["daily"],
            "weather_code": [0],
        },
    }

    with pytest.raises(ValueError, match="Daily length mismatch"):
        parse_weather_forecast(payload)


# --- fetch_weather_forecast ---


async def test_fetch_weather_forecast_success_calls_open_meteo_and_parses():
    """Verify that fetch_weather_forecast calls the API and returns a WeatherForecast."""
    mock_response = httpx.Response(200, json=OPEN_METEO_PAYLOAD, request=OPEN_METEO_REQUEST)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        forecast = await fetch_weather_forecast(30.2672, -97.7431)

    assert isinstance(forecast, WeatherForecast)
    mock_client.get.assert_awaited_once()


async def test_fetch_weather_forecast_http_status_error_raises_runtime_error():
    """Verify that an HTTP error from Open-Meteo raises RuntimeError."""
    request = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Request",
            request=request,
            response=httpx.Response(400, request=request),
        )
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="OpenMeteo API error: 400"):
            await fetch_weather_forecast(30.2672, -97.7431)


async def test_fetch_weather_forecast_invalid_json_raises_value_error():
    """Verify that invalid JSON from Open-Meteo raises ValueError."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: (_ for _ in ()).throw(ValueError("bad json"))
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.weather_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises((ValueError, RuntimeError)):
            await fetch_weather_forecast(30.2672, -97.7431)
