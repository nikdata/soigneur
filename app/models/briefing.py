"""Pydantic model for the structured daily briefing response."""

from __future__ import annotations

from pydantic import BaseModel


class BriefingResponse(BaseModel):
    """Structured response from the briefing agent.

    Splits the daily briefing into two distinct sections so the
    frontend can render them in separate widgets.

    Attributes:
        today: The workout recommendation and reasoning for today.
        tomorrow: Flags or alternatives for tomorrow's workout, or
            None if there is nothing to flag.
    """

    today: str
    tomorrow: str | None = None
