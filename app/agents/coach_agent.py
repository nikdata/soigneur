"""
PydanticAI agent for the Soigneur coach assistant for use in a CLI loop.
"""

from __future__ import annotations

import asyncio

from pydantic_ai import Agent
from datetime import date, datetime
from pathlib import Path
import yaml

from app.config import get_settings
from app.models.briefing import BriefingResponse
from app.services.goals_service import fetch_goals as get_goals
from app.services.trainerroad_service import (
    get_planned_workouts as get_upcoming_workouts,
)
from app.services.weather_service import (
    fetch_weather_forecast as get_weather,
    resolve_zipcode,
)
from app.services.activity_service import get_list_of_activities as get_activities
from app.services.wellness_service import get_wellness

# load rider profile once at import time
profile_path = Path(__file__).parent.parent / "config" / "profile.yaml"
with open(profile_path) as f:
    rider_profile = yaml.safe_load(f)


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""\
Today's date is {date.today().isoformat()}. Current local time is {datetime.now().strftime("%I:%M %p")}.

## Rider Profile
{yaml.dump(rider_profile, default_flow_style=False)}

You are a cycling coach assistant. You help the rider decide whether to
complete today's planned workout, modify it, skip it, or go for an
unstructured outdoor ride instead.

## Daily Recommendation Logic
Follow this decision tree when making today's training recommendation:

1. Check if a workout is scheduled today.
2. If yes, evaluate whether it aligns with the rider's goals:
   - C-priority events with completion targets do not need high-intensity work. Favor endurance and time in the saddle.
   - Only recommend VO2max or threshold work if the goal is A-priority with a performance target.
   - If the workout does not align, propose a specific alternative that fits within the rider's max workout duration.
3. Check weather and recent activity history:
   - If weather is good and the rider has been doing mostly indoor structured work, recommend an unstructured outdoor ride instead.
   - If weather is bad, recommend the scheduled indoor workout (or the alternative from step 2).
4. Check wellness data for recovery signals:
   - HRV (rMSSD from Oura — lower is worse)
   - Sleep score (0-100 from Oura)
   - Sleep quality (1-5 scale)
   - Readiness score (0-100 from Oura)
   - Resting HR (elevated = fatigue signal)
   - CTL (chronic training load / fitness)
   - ATL (acute training load / fatigue)
   - Ramp rate (how fast load is increasing)

   Interpretation guide:
   - Readiness below 60 or sleep score below 60: lean toward rest or easy outdoor ride
   - ATL significantly above CTL (high fatigue relative to fitness): reduce intensity
   - Ramp rate above 7: training load increasing too fast, consider a recovery day

   If recent activities show high accumulated load or the rider has had multiple hard days in a row, recommend a rest day regardless of what's scheduled.
5. If no workout is scheduled today, check weather and suggest an easy outdoor ride if conditions are good and the rider's schedule allows it. Otherwise, confirm it's a rest day.
6. After today's recommendation, check tomorrow's scheduled workout.
   - If it does not align with the rider's goals, flag it and propose an alternative workout type.
   - Keep this brief — one sentence on the mismatch, one sentence on what to replace it with.
   - The rider will manually update TrainerRoad.

Structured workouts are always indoors. Outdoor rides are always unstructured.

## Available Tools
- Rider goals (events, priorities, target outcomes)
- Weather forecast for the rider's location
- Upcoming scheduled workouts from TrainerRoad
- Recent completed activities
- Today's wellness data (HRV, sleep, readiness, training load)

## Response Style
- No emojis.
- No preamble or introduction.
- Be concise. Short paragraphs, no filler.
- State the recommendation first, then the reasoning.
- Maximum 3-4 sentences for simple questions.
- Only elaborate when the user asks for reasoning or details.
- Do not volunteer scheduling logistics unless asked.
- If the user says "refresh" or "check again", re-fetch all data from tools instead of using previously fetched results.

## Daily Briefing Format
When giving the daily briefing, populate the structured response fields:

- **today**: Put everything about today here — what's scheduled (or "rest day"),
  the coach's recommendation, and the reasoning. Be concise.
- **tomorrow**: Put any flags or alternatives for tomorrow's workout here.
  If tomorrow's workout aligns with the rider's goals and there is nothing to
  flag, set this to null.
"""

# ---------------------------------------------------------------------------
# AGENT DEFINITION
# ---------------------------------------------------------------------------

coach_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    instructions=SYSTEM_PROMPT,
)

briefing_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    instructions=SYSTEM_PROMPT,
    output_type=BriefingResponse,
)

# ---------------------------------------------------------------------------
# TOOLS — thin wrappers around service functions
# ---------------------------------------------------------------------------


async def _fetch_goals() -> str:
    """Fetch the rider's goals including events with dates, types, priorities, and target outcomes."""
    goals = await get_goals()
    return "\n".join(g.model_dump_json() for g in goals)


async def _fetch_weather() -> str:
    """Fetch the weather forecast for the rider's location."""
    coords = await resolve_zipcode()
    forecast = await get_weather(coords.lat, coords.lon)
    return forecast.model_dump_json()


async def _fetch_upcoming_workouts() -> str:
    """Fetch the upcoming workouts for the rider."""
    workouts = await get_upcoming_workouts()
    return "\n".join(w.model_dump_json() for w in workouts)


async def _fetch_activities() -> str:
    """Fetch the recent activities for the rider."""
    activities = await get_activities()
    return "\n".join(a.model_dump_json() for a in activities)


async def _fetch_wellness() -> str:
    """Fetch recent wellness data (HRV, sleep, readiness, training load)."""
    wellness = await get_wellness()
    return "\n".join(w.model_dump_json() for w in wellness)


for _agent in (coach_agent, briefing_agent):

    @_agent.tool_plain
    async def fetch_goals() -> str:
        """Fetch the rider's goals which includes events with dates, types, priorities, and target outcomes."""
        return await _fetch_goals()

    @_agent.tool_plain
    async def fetch_weather() -> str:
        """Fetch the weather forecast for the rider's location."""
        return await _fetch_weather()

    @_agent.tool_plain
    async def fetch_upcoming_workouts() -> str:
        """Fetch the upcoming workouts for the rider."""
        return await _fetch_upcoming_workouts()

    @_agent.tool_plain
    async def fetch_activities() -> str:
        """Fetch the recent activities for the rider."""
        return await _fetch_activities()

    @_agent.tool_plain
    async def fetch_wellness() -> str:
        """Fetch recent wellness data (HRV, sleep, readiness, training load)."""
        return await _fetch_wellness()

# ---------------------------------------------------------------------------
# CLI LOOP — for testing before wiring up FastAPI
# ---------------------------------------------------------------------------


async def main() -> None:
    message_history = None

    # Daily briefing on startup
    briefing_prompt = (
        "Give me today's training recommendation. Check my scheduled workout, "
        "goals, recent activities, and weather. Tell me what to do today."
    )

    result = await coach_agent.run(briefing_prompt, message_history=message_history)
    message_history = result.all_messages()
    print(f"\nCoach: {result.output}")

    # Then drop into the interactive loop
    while True:
        user_input = input("\n> ").strip()
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        result = await coach_agent.run(user_input, message_history=message_history)
        message_history = result.all_messages()
        print(f"\nCoach: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
