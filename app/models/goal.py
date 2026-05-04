"""
Pydantic models for goals data.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date as d
from typing import Literal

GoalType = Literal["race", "charity", "fitness", "sportive", "none"]
GoalPriority = Literal["A", "B", "C"]

class Goal(BaseModel):
    """
    A goal for a given date.
    """

    name: str = Field(..., description="The name of the goal")
    date: d = Field(..., description="The date of the goal")
    days: int = Field(1, description="The number of days the goal spans")
    type: GoalType = Field(..., description="The type of the goal")
    priority: GoalPriority = Field(..., description="The priority of the goal")
    description: str = Field(..., description="The description of the goal")
    target_outcome: str = Field(..., description="The target outcome of the goal")

class GoalConfig(BaseModel):
    """Container for the list of goals loaded from config/goals.yaml."""
    goals: list[Goal]