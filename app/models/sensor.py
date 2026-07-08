from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    sensor_id: str
    zone_id: str
    zone_name: str
    timestamp: datetime
    temperature_f: float = Field(..., description="Temperature in Fahrenheit")
    humidity_pct: float = Field(..., description="Relative humidity (0–100)")
    wind_speed_mph: float = Field(..., description="Wind speed in mph")
    pm25_ugm3: float = Field(..., description="PM2.5 particulate matter in μg/m³")
    battery_pct: float = Field(..., description="Sensor battery level (0–100)")
    latitude: float
    longitude: float
    wildfire_risk: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


class SensorMeta(BaseModel):
    sensor_id: str
    zone_id: str
    zone_name: str
    latitude: float
    longitude: float
    active: bool = True


class BulkReadingsResponse(BaseModel):
    sensor_count: int
    reading_count: int
    start: datetime
    end: datetime
    interval_seconds: int
    readings: list[SensorReading]
