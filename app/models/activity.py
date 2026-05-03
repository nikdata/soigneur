"""
Pydantic model for activity data.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime as dt, date as d

class ZoneTime(BaseModel):
    """Time spent in a specific power zone."""
    id: str = Field(..., description="Zone identifier (e.g., Z1, Z2, SS)")
    secs: int = Field(..., description="Seconds spent in this zone")

class Activity(BaseModel):
    """
    Activity data for a given activity
    """
    id: str = Field(..., alias="id", description="The id of the activity")
    name: str = Field(..., alias="name", description="The name of the activity")
    start_date_local: dt = Field(..., alias="start_date_local", description="The start date and time of the activity")
    type: str = Field(..., alias="type", description="The type of the activity")
    moving_time: int = Field(..., alias="moving_time", description="The moving time of the activity")
    icu_training_load: float | None = Field(None, alias="icu_training_load", description="The training load of the activity")
    average_heartrate: float | None = Field(None, alias="average_heartrate", description="The average heart rate of the activity")
    max_heartrate: int | None = Field(None, alias="max_heartrate", description="The max heart rate of the activity")
    calories: int | None = Field(None, alias="calories", description="The calories of the activity")
    icu_average_watts: float | None = Field(None, alias="icu_average_watts", description="The average watts of the activity")
    icu_weighted_avg_watts: float | None = Field(None, alias="icu_weighted_avg_watts", description="The weighted average watts of the activity")
    icu_intensity: float | None = Field(None, alias="icu_intensity", description="The intensity of the activity")
    compliance: float | None = Field(None, alias="compliance", description="Whether the activity was compliant")
    trainer: bool | None = Field(None, alias="trainer", description="Whether the activity was done on a trainer")
    interval_summary: list[str] | None = Field(None, alias="interval_summary", description="The interval summary of the activity")
    icu_zone_times: list[ZoneTime] | None = Field(None, alias="icu_zone_times", description="The zone times of the activity")
    distance: float | None = Field(None, alias="distance", description="The distance of the activity")
