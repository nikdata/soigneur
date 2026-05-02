"""Application configuration loaded from environment variables.

Secrets are supplied by Doppler into the process environment at runtime
via ``doppler run``.  No ``.env`` file is used — Doppler is the single
source of truth for all environments and machines.

Integration keys are optional at startup: each feature validates the variables
it needs when invoked (for example, chat requires ``ANTHROPIC_API_KEY``) so the
app can boot while dependencies are still being configured.
"""

from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings for Soigneur environment variables."""

    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key for PydanticAI / Claude; required for chat.",
    )
    intervals_api_key: str | None = Field(
        default=None,
        description="intervals.icu API key (HTTP Basic password); required for workouts/wellness.",
    )
    intervals_athlete_id: str | None = Field(
        default=None,
        description="intervals.icu athlete ID; required for workouts/wellness.",
    )
    trainerroad_ical_url: str | None = Field(
        default=None,
        description="TrainerRoad iCal subscription URL; required for upcoming workouts.",
    )
    location_zip: str | None = Field(
        default=None,
        description="User location (ZIP or city/state) for weather lookups.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance parsed from the environment.

    Returns:
        Singleton settings object.

    Note:
        Tests can call ``get_settings.cache_clear()`` when environment overrides
        must be re-read between cases.
    """
    return Settings()
