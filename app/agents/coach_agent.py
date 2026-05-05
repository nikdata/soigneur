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
from app.services.goals_service import fetch_goals as get_goals
from app.services.trainerroad_service import get_planned_workouts as get_upcoming_workouts
from app.services.weather_service import fetch_weather_forecast as get_weather, resolve_zipcode
from app.services.activity_service import get_list_of_activities as get_activities

# load rider profile once at import time
profile_path = Path(__file__).parent.parent / "config" / "profile.yaml"
with open(profile_path) as f:
    rider_profile = yaml.safe_load(f)


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""\
Today's date is {date.today().isoformat()}. Current local time is {datetime.now().strftime('%I:%M %p')}.

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
4. If recent activities show high accumulated load or the rider has had multiple hard days in a row, recommend a rest day regardless of what's scheduled.
5. If no workout is scheduled today, check weather and suggest an easy outdoor ride if conditions are good and the rider's schedule allows it. Otherwise, confirm it's a rest day.
6. After today's recommendation, check tomorrow's scheduled workout.
   - If it does not align with the rider's goals, flag it and propose an alternative workout type.
   - Keep this brief — one sentence on the mismatch, one sentence on what to replace it with.
   - The rider will manually update TrainerRoad.

Structured workouts are always indoors. Outdoor rides are always unstructured.

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
When giving the daily briefing, use this format:

Today's Workout
<what's scheduled or "rest day">

Coach's Recommendation
<what to do and why, concise>

About Tomorrow
<flag any mismatches, suggest alternatives if needed>
"""

# ---------------------------------------------------------------------------
# AGENT DEFINITION
# ---------------------------------------------------------------------------

coach_agent = Agent(
    'anthropic:claude-sonnet-4-6',
    instructions=SYSTEM_PROMPT,
)

# ---------------------------------------------------------------------------
# TOOLS — thin wrappers around service functions
# ---------------------------------------------------------------------------

@coach_agent.tool_plain
async def fetch_goals() -> str:
    """
    Fetch the rider's goals which includes events with dates, types, priorities, and target outcomes.
    """
    goals = await get_goals()
    return "\n".join(g.model_dump_json() for g in goals)

@coach_agent.tool_plain
async def fetch_weather() -> str:
    """
    Fetch the weather forecast for the rider's location.
    """
    coords = await resolve_zipcode()
    forecast = await get_weather(coords.lat, coords.lon)
    return forecast.model_dump_json()

@coach_agent.tool_plain
async def fetch_upcoming_workouts() -> str:
    """
    Fetch the upcoming workouts for the rider.
    """
    workouts = await get_upcoming_workouts()
    return "\n".join(w.model_dump_json() for w in workouts)

@coach_agent.tool_plain
async def fetch_activities() -> str:
    """
    Fetch the recent activities for the rider.
    """
    activities = await get_activities()
    return "\n".join(a.model_dump_json() for a in activities)

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

if __name__ == '__main__':
    asyncio.run(main())