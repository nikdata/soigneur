"""
Pydantic models for wellness data.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date as d


class Wellness(BaseModel):
    """
    A wellness reading for a given date.
    """

    date: d = Field(..., alias="id", description="The date of the reading")
    ctl: float = Field(..., description="The current training load")
    atl: float = Field(..., description="The current accumulated training load")
    ramp_rate: float = Field(
        ..., alias="rampRate", description="The ramp rate of the training load"
    )
    sleep_score: float | None = Field(
        None, alias="sleepScore", description="The sleep score"
    )
    sleep_quality: int | None = Field(
        None, alias="sleepQuality", description="The sleep quality"
    )
    sleep_secs: int | None = Field(
        None, alias="sleepSecs", description="The sleep duration in seconds"
    )
    sleep_avg_hr: float | None = Field(
        None, alias="avgSleepingHR", description="The average heart rate during sleep"
    )
    readiness: float | None = Field(None, description="The readiness score")
    resting_hr: float | None = Field(
        None, alias="restingHR", description="The resting heart rate in bpm"
    )
    hrv: float | None = Field(None, description="The heart rate variability in ms")
