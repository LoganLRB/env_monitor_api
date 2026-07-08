import math
import random
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.models.sensor import SensorReading

_SENSOR_CATALOG: list[dict] = [
    # Zone A: Northern Forest Ridge
    {"sensor_id": "SNS-001", "zone_id": "zone-a", "zone_name": "Northern Forest Ridge", "latitude": 37.5123, "longitude": -119.5341},
    {"sensor_id": "SNS-002", "zone_id": "zone-a", "zone_name": "Northern Forest Ridge", "latitude": 37.5187, "longitude": -119.5218},
    {"sensor_id": "SNS-003", "zone_id": "zone-a", "zone_name": "Northern Forest Ridge", "latitude": 37.5051, "longitude": -119.5482},
    # Zone B: Southern Valley Floor
    {"sensor_id": "SNS-004", "zone_id": "zone-b", "zone_name": "Southern Valley Floor", "latitude": 37.3124, "longitude": -119.2987},
    {"sensor_id": "SNS-005", "zone_id": "zone-b", "zone_name": "Southern Valley Floor", "latitude": 37.3253, "longitude": -119.3152},
    {"sensor_id": "SNS-006", "zone_id": "zone-b", "zone_name": "Southern Valley Floor", "latitude": 37.3015, "longitude": -119.2871},
    # Zone C: Eastern Canyon
    {"sensor_id": "SNS-007", "zone_id": "zone-c", "zone_name": "Eastern Canyon",        "latitude": 37.4213, "longitude": -119.1983},
    {"sensor_id": "SNS-008", "zone_id": "zone-c", "zone_name": "Eastern Canyon",        "latitude": 37.4352, "longitude": -119.2114},
    {"sensor_id": "SNS-009", "zone_id": "zone-c", "zone_name": "Eastern Canyon",        "latitude": 37.4091, "longitude": -119.1852},
    # Zone D: Western Meadow
    {"sensor_id": "SNS-010", "zone_id": "zone-d", "zone_name": "Western Meadow",        "latitude": 37.4481, "longitude": -119.6234},
    {"sensor_id": "SNS-011", "zone_id": "zone-d", "zone_name": "Western Meadow",        "latitude": 37.4614, "longitude": -119.6381},
    {"sensor_id": "SNS-012", "zone_id": "zone-d", "zone_name": "Western Meadow",        "latitude": 37.4371, "longitude": -119.6112},
]

_ZONES: list[str] = list({s["zone_id"] for s in _SENSOR_CATALOG})


def _diurnal_offset(hour: int) -> float:
    """Temperature swing by time of day. Peak ~3 PM (hour=15), trough ~5 AM (hour=5)."""
    return 14.0 * math.sin(math.pi * (hour - 5) / 12.0)


def _classify_risk(temp_f: float, humidity_pct: float) -> Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]:
    if temp_f > 110 and humidity_pct < 15:
        return "CRITICAL"
    if temp_f > 100 and humidity_pct < 25:
        return "HIGH"
    if temp_f > 90 and humidity_pct < 35:
        return "MODERATE"
    return "LOW"


def generate_reading(sensor: dict, ts: datetime, fire_event: bool = False) -> SensorReading:
    base_temp = 78.0 + _diurnal_offset(ts.hour)

    if fire_event:
        temp = random.uniform(108.0, 133.0)
        humidity = random.uniform(7.0, 15.0)
        wind = random.uniform(18.0, 40.0)
        pm25 = random.uniform(90.0, 350.0)
    else:
        temp = base_temp + random.gauss(0, 3.0)
        humidity = max(10.0, min(98.0, 62.0 - (temp - 78.0) * 0.7 + random.gauss(0, 6.0)))
        wind = max(0.0, random.gauss(7.0, 4.0))
        pm25 = max(0.0, random.gauss(11.0, 5.0))

    return SensorReading(
        sensor_id=sensor["sensor_id"],
        zone_id=sensor["zone_id"],
        zone_name=sensor["zone_name"],
        timestamp=ts,
        temperature_f=round(temp, 2),
        humidity_pct=round(humidity, 2),
        wind_speed_mph=round(wind, 2),
        pm25_ugm3=round(pm25, 2),
        battery_pct=round(random.uniform(82.0, 99.5), 1),
        latitude=round(sensor["latitude"] + random.gauss(0, 0.00005), 6),
        longitude=round(sensor["longitude"] + random.gauss(0, 0.00005), 6),
        wildfire_risk=_classify_risk(temp, humidity),
    )


def sample_zone_fire_events(probability: float = 0.05) -> dict[str, bool]:
    return {zone_id: random.random() < probability for zone_id in _ZONES}


def get_all_sensors() -> list[dict]:
    return _SENSOR_CATALOG


def generate_bulk_readings(
    start: datetime,
    end: datetime,
    interval_seconds: int = 300,
    zone_id: str | None = None,
    fire_probability: float = 0.05,
) -> list[SensorReading]:
    sensors = [s for s in _SENSOR_CATALOG if zone_id is None or s["zone_id"] == zone_id]

    # Per-zone fire state; autocorrelated so events persist across intervals.
    zone_fire_state: dict[str, bool] = {z: False for z in _ZONES}

    readings: list[SensorReading] = []
    ts = start
    while ts <= end:
        for zone in _ZONES:
            if zone_fire_state[zone]:
                zone_fire_state[zone] = random.random() > 0.20  # 20% chance of ending
            else:
                zone_fire_state[zone] = random.random() < fire_probability

        for sensor in sensors:
            readings.append(generate_reading(sensor, ts, fire_event=zone_fire_state[sensor["zone_id"]]))

        ts += timedelta(seconds=interval_seconds)

    return readings
