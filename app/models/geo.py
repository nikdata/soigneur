"""
Pydantic models for geographic data.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class GeoLocation(BaseModel):
    """
    A geographic location represented by latitude and longitude.

    Used to convert a postal code to a latitude and longitude.
    """

    lat: float = Field(..., description="Latitude of the location")
    lon: float = Field(..., description="Longitude of the location")
