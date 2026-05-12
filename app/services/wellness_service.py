"""
Intervals.icu wellness service.

Fetches wellness data from the intervals.icu REST API, including sleep
metrics (score, quality, duration), readiness, HRV, resting heart rate,
and training load (CTL, ATL, ramp rate). Data originates from Oura via
the intervals.icu integration.

The main entry point is ``get_wellness()``, which returns the last 8 days
of wellness readings.
"""

from __future__ import annotations
import httpx
import json
from datetime import date, timedelta
from app.config import get_settings
from app.models.wellness import Wellness


async def get_wellness() -> list[Wellness]:

    """
    Fetch recent wellness data from intervals.icu.

    Retrieves the last 8 days of wellness readings including sleep score,
    sleep quality, HRV, readiness, resting HR, and training load metrics
    (CTL, ATL, ramp rate). Authentication and athlete ID are resolved
    internally via get_settings().

    Returns:
        List of Wellness models sorted by date from the API. Empty list
        if no wellness data exists for the window.

    Raises:
        RuntimeError: If the intervals.icu API returns a non-200 response.
        ValueError: If the API returns invalid JSON.
    """

    # get the current date and the date 8 days ago
    current_date = date.today()
    begin_date = (current_date - timedelta(days=8)).strftime("%Y-%m-%d")
    end_date = current_date.strftime("%Y-%m-%d")

    # instantiate the settings
    settings = get_settings()
    athlete_id = settings.intervals_athlete_id
    user_name = "API_KEY"
    user_password = settings.intervals_api_key

    # check to ensure that the athlete id and user name and password are set
    if not athlete_id or not user_password:
        raise ValueError("Athlete ID or password is not set")

    base_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness"
    params = {
        "oldest": begin_date,
        "newest": end_date,
        "fields": "id,restingHR,hrv,sleepSecs,sleepScore,sleepQuality,avgSleepingHR,readiness,ctl,atl,rampRate",
    }

    auth = httpx.BasicAuth(username=user_name, password=user_password)

    # async client to make the request
    async with httpx.AsyncClient(auth=auth, timeout=10.0) as client:
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Intervals.icu API error: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Intervals.icu request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format from Intervals.icu API") from e

    # check to ensure that wellness data is not empty
    if not data:
        return []  # return an empty list if no wellness data is found

    # check to ensure that the data is in the expected format
    wellness = [Wellness(**item) for item in data]

    return wellness
