"""Unit tests for app.services.activity_service."""

from __future__ import annotations
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.services.activity_service import get_list_of_activities
from app.models.activity import Activity


INTERVALS_REQUEST = httpx.Request("GET", "https://intervals.icu/api/v1/athlete/i12345/activities")

ACTIVITY_RESPONSE = [
    {
        "id": "i1001",
        "name": "Sweet Spot Base",
        "start_date_local": "2026-05-01T07:00:00",
        "type": "VirtualRide",
        "moving_time": 3600,
        "icu_training_load": 75.0,
        "average_heartrate": 145.0,
        "max_heartrate": 170,
        "calories": 650,
        "icu_average_watts": 200.0,
        "icu_weighted_avg_watts": 220.0,
        "icu_intensity": 0.78,
        "compliance": 0.95,
        "trainer": True,
        "interval_summary": ["3x12 SS"],
        "icu_zone_times": [{"id": "Z2", "secs": 1800}, {"id": "SS", "secs": 1200}],
        "distance": 0.0,
    },
    {
        "id": "i1002",
        "name": "Morning Group Ride",
        "start_date_local": "2026-05-02T06:30:00",
        "type": "Ride",
        "moving_time": 5400,
        "icu_training_load": 95.0,
        "average_heartrate": 150.0,
        "max_heartrate": 180,
        "calories": 900,
        "icu_average_watts": 210.0,
        "icu_weighted_avg_watts": 240.0,
        "icu_intensity": 0.85,
        "compliance": None,
        "trainer": False,
        "interval_summary": None,
        "icu_zone_times": None,
        "distance": 45000.0,
    },
    {
        "id": "i1003",
        "name": "Morning Run",
        "start_date_local": "2026-05-02T08:00:00",
        "type": "Run",
        "moving_time": 2400,
        "icu_training_load": 40.0,
        "average_heartrate": 155.0,
        "max_heartrate": 175,
        "calories": 350,
        "icu_average_watts": None,
        "icu_weighted_avg_watts": None,
        "icu_intensity": 0.65,
        "compliance": None,
        "trainer": False,
        "interval_summary": None,
        "icu_zone_times": None,
        "distance": 5000.0,
    },
    {
        "id": "i1004",
        "name": "Upper Body",
        "start_date_local": "2026-05-03T17:00:00",
        "type": "WeightTraining",
        "moving_time": 2700,
        "icu_training_load": 30.0,
        "average_heartrate": 120.0,
        "max_heartrate": 140,
        "calories": 250,
        "icu_average_watts": None,
        "icu_weighted_avg_watts": None,
        "icu_intensity": 0.45,
        "compliance": None,
        "trainer": False,
        "interval_summary": None,
        "icu_zone_times": None,
        "distance": 0.0,
    },
]


def _make_mock_client(response):
    """Build a mock httpx.AsyncClient that returns the given response on GET."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.fixture(autouse=True)
def _set_intervals_env(monkeypatch):
    """Inject required Intervals.icu env vars for every test in this module."""
    monkeypatch.setenv("INTERVALS_ATHLETE_ID", "i12345")
    monkeypatch.setenv("INTERVALS_API_KEY", "test-key")


async def test_get_list_of_activities_success_filters_and_parses():
    """Verify that activities are parsed and filtered to VirtualRide, Ride, WeightTraining."""
    mock_response = httpx.Response(200, json=ACTIVITY_RESPONSE, request=INTERVALS_REQUEST)
    mock_client = _make_mock_client(mock_response)

    with patch("app.services.activity_service.httpx.AsyncClient", return_value=mock_client):
        activities = await get_list_of_activities()

    assert len(activities) == 3
    assert all(isinstance(a, Activity) for a in activities)
    types = {a.type for a in activities}
    assert types == {"VirtualRide", "Ride", "WeightTraining"}
    assert not any(a.type == "Run" for a in activities)


async def test_get_list_of_activities_empty_response_returns_empty_list():
    """Verify that an empty API response returns an empty list."""
    mock_response = httpx.Response(200, json=[], request=INTERVALS_REQUEST)
    mock_client = _make_mock_client(mock_response)

    with patch("app.services.activity_service.httpx.AsyncClient", return_value=mock_client):
        activities = await get_list_of_activities()

    assert activities == []


async def test_get_list_of_activities_http_status_error_raises_runtime_error():
    """Verify that an HTTP error from Intervals.icu raises RuntimeError."""
    request = httpx.Request("GET", "https://intervals.icu/api/v1/athlete/i12345/activities")
    mock_client = _make_mock_client(None)
    mock_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Unauthorized",
            request=request,
            response=httpx.Response(401, request=request),
        )
    )

    with patch("app.services.activity_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Intervals.icu API error: 401"):
            await get_list_of_activities()


async def test_get_list_of_activities_request_error_raises_runtime_error():
    """Verify that a network-level failure raises RuntimeError."""
    mock_client = _make_mock_client(None)
    mock_client.get = AsyncMock(
        side_effect=httpx.RequestError("Connection timed out")
    )

    with patch("app.services.activity_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Intervals.icu request failed"):
            await get_list_of_activities()


async def test_get_list_of_activities_invalid_json_raises_value_error():
    """Verify that invalid JSON from Intervals.icu raises ValueError."""
    mock_client = _make_mock_client(None)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: (_ for _ in ()).throw(ValueError("bad json"))
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.activity_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises((ValueError, RuntimeError)):
            await get_list_of_activities()


async def test_get_list_of_activities_nullable_fields_parsed():
    """Verify that activities with null optional fields parse without error."""
    minimal = [
        {
            "id": "i2000",
            "name": "Easy Spin",
            "start_date_local": "2026-05-03T08:00:00",
            "type": "Ride",
            "moving_time": 1800,
            "icu_training_load": None,
            "average_heartrate": None,
            "max_heartrate": None,
            "calories": None,
            "icu_average_watts": None,
            "icu_weighted_avg_watts": None,
            "icu_intensity": None,
            "compliance": None,
            "trainer": None,
            "interval_summary": None,
            "icu_zone_times": None,
            "distance": None,
        }
    ]
    mock_response = httpx.Response(200, json=minimal, request=INTERVALS_REQUEST)
    mock_client = _make_mock_client(mock_response)

    with patch("app.services.activity_service.httpx.AsyncClient", return_value=mock_client):
        activities = await get_list_of_activities()

    assert len(activities) == 1
    a = activities[0]
    assert a.icu_training_load is None
    assert a.average_heartrate is None
    assert a.trainer is None
