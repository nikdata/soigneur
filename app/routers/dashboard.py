"""Dashboard router for Soigneur.

Handles the main page render, the async daily briefing endpoint,
and the chat interaction with the coach agent.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import markdown

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic_ai.messages import ModelMessage

from app.models.planned_workout import PlannedWorkout
from app.models.weather import HourlyWeather
from app.services.goals_service import fetch_goals
from app.services.trainerroad_service import get_planned_workouts
from app.services.weather_service import fetch_weather_forecast, resolve_zipcode
from app.services.activity_service import get_list_of_activities
from app.agents.coach_agent import briefing_agent, coach_agent

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
router = APIRouter()

message_history: list[ModelMessage] = []


def _today_workout(workouts: list[PlannedWorkout]) -> PlannedWorkout | None:
    """Return the first workout scheduled for today, or None."""
    today = date.today()
    return next((w for w in workouts if w.date == today), None)


def _next_hours(hourly: list[HourlyWeather], hours: int = 8) -> list[HourlyWeather]:
    """Return the next *hours* of hourly forecasts starting from the current hour."""
    now = datetime.now()
    upcoming = [h for h in hourly if h.datetime >= now.replace(minute=0, second=0)]
    return upcoming[:hours]


def _summarize_upcoming_weather(hours: list[HourlyWeather]) -> str:
    """Build a 1-3 sentence summary of the next 8 hours from hourly data.

    Covers temperature trend, precipitation risk, and wind/gust ranges.
    No LLM involved — purely deterministic.

    Args:
        hours: The next 8 hours of hourly weather data.

    Returns:
        A plain-text summary string.
    """
    if not hours:
        return "No hourly forecast data available."

    temps = [h.temperature for h in hours]
    temp_min, temp_max = min(temps), max(temps)
    first_temp = hours[0].temperature

    if temp_max - first_temp > 3:
        peak = next(h for h in hours if h.temperature == temp_max)
        temp_part = (
            f"Temperatures rising to {temp_max:.0f}°F"
            f" by {peak.datetime.strftime('%-I %p').lower()}."
        )
    elif first_temp - temp_min > 3:
        low = next(h for h in hours if h.temperature == temp_min)
        temp_part = (
            f"Temperatures falling to {temp_min:.0f}°F"
            f" by {low.datetime.strftime('%-I %p').lower()}."
        )
    else:
        avg = sum(temps) / len(temps)
        temp_part = f"Temperature steady around {avg:.0f}°F."

    risky = [h for h in hours if h.precipitation_probability > 20]
    if risky:
        probs = [h.precipitation_probability for h in risky]
        lo, hi = min(probs), max(probs)
        prob_range = f"{lo}%" if lo == hi else f"{lo}–{hi}%"
        start_label = risky[0].datetime.strftime("%-I %p")
        end_label = risky[-1].datetime.strftime("%-I %p")
        if start_label == end_label:
            precip_part = f"Rain possible around {start_label} ({prob_range} chance)."
        else:
            precip_part = (
                f"Rain likely between {start_label} and {end_label}"
                f" ({prob_range} chance)."
            )
    else:
        ceiling = max(h.precipitation_probability for h in hours)
        if ceiling == 0:
            precip_part = "No precipitation expected."
        else:
            precip_part = f"Precipitation unlikely — all hours at {ceiling}% or below."

    winds = [h.wind_speed for h in hours]
    gusts = [h.wind_gusts for h in hours]
    wind_min, wind_max = min(winds), max(winds)
    gust_max = max(gusts)

    if wind_max - wind_min <= 3:
        avg_wind = sum(winds) / len(winds)
        wind_desc = f"around {avg_wind:.0f}"
    else:
        wind_desc = f"{wind_min:.0f}–{wind_max:.0f}"

    if gust_max > wind_max + 5:
        peak_gust = next(h for h in hours if h.wind_gusts == gust_max)
        wind_part = (
            f"Wind {wind_desc} mph with gusts to {gust_max:.0f} mph"
            f" by {peak_gust.datetime.strftime('%-I %p').lower()}."
        )
    else:
        wind_part = f"Wind {wind_desc} mph."

    return f"{temp_part} {precip_part} {wind_part}"


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main dashboard page.

    Fetches goals, planned workouts, weather, and recent activities in
    parallel, then renders the index template with all data in context.

    Args:
        request: The incoming HTTP request.

    Returns:
        Rendered HTML response for the main page.
    """
    goals, workouts, geo, activities = await asyncio.gather(
        fetch_goals(),
        get_planned_workouts(days_ahead=7),
        resolve_zipcode(),
        get_list_of_activities(),
    )
    weather = await fetch_weather_forecast(geo.lat, geo.lon)
    upcoming_hours = _next_hours(weather.hourly)

    context: dict[str, Any] = {
        "goals": goals,
        "workouts": workouts,
        "weather": weather,
        "activities": activities,
        "today_workout": _today_workout(workouts),
        "weather_summary": _summarize_upcoming_weather(upcoming_hours),
    }
    return templates.TemplateResponse(request, "index.html", context)


@router.get("/briefing", response_class=HTMLResponse)
async def briefing(request: Request) -> HTMLResponse:
    """Generate the daily coaching briefing via the agent.

    Runs the coach agent with the daily briefing prompt and stores
    the resulting message history so the chat can continue from
    this context.

    Args:
        request: The incoming HTTP request.

    Returns:
        HTMX partial with the agent's daily briefing.
    """
    global message_history

    briefing_prompt = (
        "Give me today's training recommendation. Check my scheduled workout, "
        "goals, recent activities, and weather. Tell me what to do today."
    )

    result = await briefing_agent.run(briefing_prompt, message_history=None)
    message_history = list(result.all_messages())

    today_html = markdown.markdown(result.output.today, extensions=["nl2br"])
    tomorrow_html = (
        markdown.markdown(result.output.tomorrow, extensions=["nl2br"])
        if result.output.tomorrow
        else None
    )

    return templates.TemplateResponse(
        request,
        "partials/briefing.html",
        {"today": today_html, "tomorrow": tomorrow_html},
    )


@router.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, message: str = Form(...)) -> HTMLResponse:
    """Process a chat message through the coach agent.

    Appends the user message and agent response to the conversation
    history so the agent maintains context across turns.

    Args:
        request: The incoming HTTP request.
        message: The user's chat message from the form submission.

    Returns:
        HTMX partial with both the user message and the agent response.
    """
    global message_history

    result = await coach_agent.run(message, message_history=message_history)
    message_history = list(result.all_messages())

    agent_html = markdown.markdown(result.output, extensions=["nl2br"])

    return templates.TemplateResponse(
        request,
        "partials/chat_message.html",
        {"user_message": message, "agent_message": agent_html},
    )
