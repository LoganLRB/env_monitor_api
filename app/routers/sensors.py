import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.models.sensor import BulkReadingsResponse, SensorMeta, SensorReading
from app.services import simulator

router = APIRouter()


@router.get("", response_model=list[SensorMeta], summary="List all sensor metadata")
async def list_sensors():
    return simulator.get_all_sensors()


@router.get("/readings", response_model=list[SensorReading], summary="Current snapshot from all sensors")
async def current_readings():
    now = datetime.now(timezone.utc)
    zone_fire = simulator.sample_zone_fire_events(settings.wildfire_event_probability)
    return [
        simulator.generate_reading(s, now, fire_event=zone_fire[s["zone_id"]])
        for s in simulator.get_all_sensors()
    ]


@router.get(
    "/readings/bulk",
    response_model=BulkReadingsResponse,
    summary="Historical bulk readings — consumed by env_monitor_batch",
)
async def bulk_readings(
    hours: Annotated[int, Query(ge=1, le=72, description="Hours of history to generate")] = 24,
    interval_seconds: Annotated[int, Query(ge=60, le=3600, description="Seconds between readings per sensor")] = 300,
    zone_id: Annotated[str | None, Query(description="Filter to a single zone (e.g. zone-a)")] = None,
):
    readings = simulator.generate_bulk_readings(
        hours=hours,
        interval_seconds=interval_seconds,
        zone_id=zone_id,
        fire_probability=settings.wildfire_event_probability,
    )
    return BulkReadingsResponse(
        sensor_count=len({r.sensor_id for r in readings}),
        reading_count=len(readings),
        hours=hours,
        interval_seconds=interval_seconds,
        readings=readings,
    )


async def _event_stream():
    """
    Yields SSE-formatted sensor readings continuously.
    - One reading per sensor per interval cycle.
    - Zone-level fire events are correlated within a cycle.
    - A keepalive comment is sent every 3 cycles to prevent proxy timeouts.
    """
    tick = 0
    while True:
        zone_fire = simulator.sample_zone_fire_events(settings.wildfire_event_probability)
        now = datetime.now(timezone.utc)
        for sensor in simulator.get_all_sensors():
            reading = simulator.generate_reading(sensor, now, fire_event=zone_fire[sensor["zone_id"]])
            yield f"event: sensor_reading\ndata: {reading.model_dump_json()}\n\n"
        tick += 1
        if tick % 3 == 0:
            yield ": keepalive\n\n"
        await asyncio.sleep(settings.stream_interval_seconds)


@router.get("/stream", summary="SSE stream of live sensor readings — consumed by env_monitor_streaming")
async def stream_readings():
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
