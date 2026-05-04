"""
Pydantic model for planned workout data from TrainerRoad
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime as dt, date as d


class PlannedWorkout(BaseModel):
    """
    A planned workout from TrainerRoad
    """
    date: d = Field(..., description="The date of the workout")
    name: str = Field(..., description="The name of the workout")
    duration_minutes: int | None = Field(None, description="The duration of the workout in minutes")
    tss: int | None = Field(None, description="The TSS of the workout")
    intensity_factor: float | None = Field(None, description="The intensity factor of the workout")
    predicted_calories: int | None = Field(None, description="The predicted calories of the workout")
    description: str | None = Field(None, description="The description of the workout")
