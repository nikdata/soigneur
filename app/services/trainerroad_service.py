"""
TrainerRoad planned workout service.

Fetches the TrainerRoad iCal calendar feed and parses VEVENT entries into
PlannedWorkout models. The iCal DESCRIPTION field is parsed to extract
TSS, IF, predicted calories, and the workout description (goals text is
stripped). Rest days are excluded.

The main entry point is ``get_planned_workouts()``, which returns workouts
from today through a configurable number of days ahead.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pydantic import ValidationError

import httpx
from icalendar import Calendar

from app.config import get_settings
from app.models.planned_workout import PlannedWorkout

def vevent_dtstart_to_date(dtstart: object | None) -> date | None:
    """Return a calendar date from a VEVENT DTSTART property, or None if missing."""
    if dtstart is None:
        return None
    raw = getattr(dtstart, "dt", None)
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    return None


def ical_text(prop: object | None) -> str:
    """Decode SUMMARY/DESCRIPTION (vText) to a plain string."""
    if prop is None:
        return ""
    raw = getattr(prop, "dt", prop)
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def parse_summary_hh_mm(summary: str) -> tuple[int | None, str]:
    """
    Parse TrainerRoad SUMMARY like ``0:45 - Garin`` (HH:MM - name).

    Returns (duration_minutes, name). If the pattern does not match, duration is
    None and the whole string is returned as the name.
    """
    summary = summary.strip()
    sep = " - "
    if sep not in summary:
        return None, summary
    
    time_part, name = summary.split(sep, 1)
    time_part = time_part.strip()
    name = name.strip()
    if not name:
        return None, summary
    if ":" not in time_part:
        return None, summary
    try:
        hours_s, minutes_s = time_part.split(":", 1)
        hours = int(hours_s.strip())
        minutes = int(minutes_s.strip())
        if hours < 0 or minutes < 0 or minutes >= 60:
            return None, summary
        duration = hours * 60 + minutes
    except ValueError:
        return None, summary
    return duration, name


def parse_trainerroad_description(
    desc: str,
) -> tuple[int | None, float | None, int | None, str | None]:
    """
    Parse TrainerRoad DESCRIPTION prefix (TSS, IF, kJ(Cal)) and optional narrative.

    The narrative is taken from the substring after ``Description:`` when present.

    The returned description does not include the Goals section.
    """
    if not desc or not desc.strip():
        return None, None, None, None
    text = desc.strip()
    tss_m = re.search(r"TSS\s+(\d+)", text, re.IGNORECASE)
    if_m = re.search(r"\bIF\s+([\d.]+)", text, re.IGNORECASE)
    kj_m = re.search(r"kJ\s*\(\s*Cal\s*\)\s+(\d+)", text, re.IGNORECASE)

    tss = None
    if tss_m:
        try:
            tss = int(tss_m.group(1))
        except ValueError:
            tss = None
    
    intensity = None
    if if_m:
        try:
            intensity = float(if_m.group(1))
        except ValueError:
            intensity = None
    
    calories = None
    if kj_m:
        try:
            calories = int(kj_m.group(1))
        except ValueError:
            calories = None
    
    desc_m = re.search(r"Description:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    body = desc_m.group(1).strip() if desc_m else None
    if body:
        body = re.split(r"\s+Goals:\s*", body, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return tss, intensity, calories, body


def planned_workout_from_vevent(event: object) -> PlannedWorkout | None:
    """
    Build a PlannedWorkout from a single VEVENT, or None if it should be skipped.

    Rest days are skipped (no model instance). Events without a usable DTSTART
    are skipped.
    """
    get = getattr(event, "get", None)
    if get is None:
        return None
    summary = ical_text(get("SUMMARY"))
    if not summary.strip() or "Rest Day" in summary:
        return None
    desc = ical_text(get("DESCRIPTION"))
    d = vevent_dtstart_to_date(get("DTSTART"))
    if d is None:
        return None
    duration_minutes, name = parse_summary_hh_mm(summary)
    tss, intensity_factor, predicted_calories, description = (
        parse_trainerroad_description(desc)
    )
    return PlannedWorkout(
        date=d,
        name=name,
        duration_minutes=duration_minutes,
        tss=tss,
        intensity_factor=intensity_factor,
        predicted_calories=predicted_calories,
        description=description,
    )


async def get_planned_workouts(days_ahead: int = 5) -> list[PlannedWorkout]:
    """
    Fetch upcoming planned workouts from the TrainerRoad iCal feed.

    Retrieves the full calendar, filters to workouts from today through
    ``days_ahead`` days out, and returns them sorted by date. Rest days
    are excluded.

    Args:
        days_ahead: Number of days ahead to include. Defaults to 5.

    Returns:
        Planned workouts sorted by date, earliest first.
    """

    settings = get_settings()
    url = settings.trainerroad_ical_url

    if not url:
        raise RuntimeError("TrainerRoad iCal URL is not configured.")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise RuntimeError("TrainerRoad iCal URL must be an http(s) URL.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            cal = Calendar.from_ical(response.text)
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"TrainerRoad iCal API error: {e.response.status_code} "
                f"for {e.request.url.host}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"TrainerRoad iCal request failed: {e}") from e
        except ValueError as e:
            raise RuntimeError("TrainerRoad iCal response is not valid iCalendar data") from e


    today = date.today()
    end_inclusive = today + timedelta(days = days_ahead)

    in_window: list[PlannedWorkout] = []
    for event in cal.walk("VEVENT"):
        try:
            workout = planned_workout_from_vevent(event)
        except ValidationError:
            continue
        if workout is None:
            continue
        if today <= workout.date <= end_inclusive:
            in_window.append(workout)

    return sorted(in_window, key=lambda w: w.date)