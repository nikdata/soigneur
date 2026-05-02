"""
Pydantic models for weather forecast data.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from datetime import datetime as dt, date as d

WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Slight or moderate thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

class CurrentWeather(BaseModel):
    """
    A current weather reading for a given latitude and longitude.
    """
    datetime: dt = Field(..., description="The date and time of the reading")
    temperature: float = Field(..., description="The temperature in Fahrenheit")
    relative_humidity: float = Field(..., description="The relative humidity in percent")
    weather_code: int = Field(..., description="The weather code from the WMO code set")
    wind_speed: float = Field(..., description="The wind speed in mph")
    wind_direction: int = Field(..., description="The wind direction in degrees")
    wind_gusts: float = Field(..., description="The wind gusts in mph")
    precipitation: float = Field(..., description="The precipitation in inches")
    description: str = Field(default="", description="The description of the weather")

    @model_validator(mode="after")
    def resolve_weather_description(self) -> CurrentWeather:
        """
        Look up the weather description from the WMO code.
        """
        if not self.description:
            self.description = WMO_CODES.get(self.weather_code, "Unknown")
        return self

class DailyWeather(BaseModel):
    """
    A daily weather forecast for a given latitude and longitude.
    """
    date: d = Field(..., description="The date of the forecast")
    weather_code: int = Field(..., description="The weather code from the WMO code set")
    temperature_max: float = Field(..., description="The maximum temperature in Fahrenheit")
    temperature_min: float = Field(..., description="The minimum temperature in Fahrenheit")
    wind_speed_max: float = Field(..., description="The maximum wind speed in mph")
    wind_gusts_max: float = Field(..., description="The maximum wind gusts in mph")
    wind_direction_dominant: int = Field(..., description="The dominant wind direction in degrees")
    precipitation_sum: float = Field(..., description="The precipitation in inches")
    precipitation_probability_max: int = Field(..., description="The maximum precipitation probability in percent")
    description: str = Field(default="", description="The description of the weather")

    @model_validator(mode="after")
    def resolve_weather_description(self) -> DailyWeather:
        """
        Look up the weather description from the WMO code.
        """
        if not self.description:
            self.description = WMO_CODES.get(self.weather_code, "Unknown")
        return self

class HourlyWeather(BaseModel):
    """
    A hourly weather reading for a given latitude and longitude.
    """
    datetime: dt = Field(..., description="The date and time of the reading")
    temperature: float = Field(..., description="The temperature in Fahrenheit")
    relative_humidity: float = Field(..., description="The relative humidity in percent")
    precipitation_probability: int = Field(..., description="The precipitation probability in percent")
    precipitation: float = Field(..., description="The precipitation in inches")
    weather_code: int = Field(..., description="The weather code from the WMO code set")
    wind_speed: float = Field(..., description="The wind speed in mph")
    wind_gusts: float = Field(..., description="The wind gusts in mph")
    wind_direction: int = Field(..., description="The wind direction in degrees")
    description: str = Field(default="", description="The description of the weather")

    @model_validator(mode="after")
    def resolve_weather_description(self) -> HourlyWeather:
        """
        Look up the weather description from the WMO code.
        """
        if not self.description:
            self.description = WMO_CODES.get(self.weather_code, "Unknown")
        return self

class WeatherForecast(BaseModel):
    """
    Complete weather response including current, daily, and hourly readings.
    """
    current: CurrentWeather
    daily: list[DailyWeather]
    hourly: list[HourlyWeather]