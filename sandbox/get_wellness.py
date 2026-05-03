"""
This script will fetch the wellness data from intervals.icu
"""

from __future__ import annotations
import asyncio
import httpx
import json
from datetime import date, timedelta
from app.config import get_settings
from app.models.wellness import Wellness


current_date = date.today()
begin_date = (current_date - timedelta(days=8)).strftime("%Y-%m-%d")
end_date = current_date.strftime("%Y-%m-%d")


async def get_wellness():
    # instantiate the settings
    settings = get_settings()
    athlete_id = settings.intervals_athlete_id
    user_name = 'API_KEY'
    user_password = settings.intervals_api_key

    # check to ensure that the athlete id and user name and password are set
    if not athlete_id or not user_password:
        raise ValueError("Athlete ID or password is not set")

    base_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness"
    params = {
        "oldest": begin_date,
        "newest": end_date,
        "fields": "id,restingHR,hrv,sleepSecs,sleepScore,sleepQuality,avgSleepingHR,readiness,ctl,atl,rampRate"
    }

    auth = httpx.BasicAuth(username=user_name, password=user_password)
    
    # async client to make the request
    async with httpx.AsyncClient(auth=auth, timeout=10.0) as client:
        try:
            response = await client.get(base_url, params = params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Intervals.icu API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Intervals.icu request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON format from Intervals.icu API") from e
    
    # check to ensure that wellness data is not empty
    if not data:
        raise ValueError("No wellness data found")
    
    # check to ensure that the data is in the expected format
    wellness = [Wellness(**item) for item in data]
    
    return wellness

if __name__ == "__main__":
    wellness = asyncio.run(get_wellness())
    print(wellness)
    
    # print("Wellness Data: \n\n", json.dumps(wellness, indent=2))