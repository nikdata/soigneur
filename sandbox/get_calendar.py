"""Sandbox script to explore the TrainerRoad iCal feed."""

from __future__ import annotations

import asyncio
import httpx
from icalendar import Calendar
from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    url = settings.trainerroad_ical_url

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    cal = Calendar.from_ical(response.text)

    for event in list(cal.walk("VEVENT"))[:10]:
        summary = str(event.get("SUMMARY"))
        desc = str(event.get("DESCRIPTION"))
        if "Rest Day" not in summary:
            print("SUMMARY:", summary)
            print("DESCRIPTION:", desc)
            print("---")


asyncio.run(main())