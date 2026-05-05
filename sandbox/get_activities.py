"""
This script will fetch the activities from intervals.icu
"""

from __future__ import annotations
import asyncio
import httpx
import json
from datetime import date, timedelta
from app.config import get_settings
from app.models.activity import Activity, ZoneTime

current_date = date.today()
begin_date = (current_date - timedelta(days=5)).strftime("%Y-%m-%d")
end_date = current_date.strftime("%Y-%m-%d")


async def get_list_of_activities():

    # instantiate the settings
    settings = get_settings()
    athlete_id = settings.intervals_athlete_id
    user_name = "API_KEY"
    user_password = settings.intervals_api_key

    base_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
    params = {
        "oldest": begin_date,
        "newest": end_date,
        "fields": "id,name,start_date_local,type,name,moving_time,icu_training_load,average_heartrate,max_heartrate,calories,icu_average_watts,icu_weighted_avg_watts,icu_intensity,compliance,trainer,interval_summary,icu_zone_times,distance",
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
        raise ValueError("No activity list data found")

    activity = [Activity(**item) for item in data]

    # filter out for specific activities
    activity_types = {"VirtualRide", "Ride", "WeightTraining"}
    filtered_activities = [a for a in activity if a.type in activity_types]

    # return activity
    return filtered_activities
    # return data


if __name__ == "__main__":
    activity = asyncio.run(get_list_of_activities())
    print(activity)

    # print("Activity List: \n\n", json.dumps(wellness, indent=2))
    # print(json.dumps(wellness, indent=2))
