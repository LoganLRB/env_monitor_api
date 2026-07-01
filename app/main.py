from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health, sensors

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Mock IoT sensor data generator for wildfire and environmental monitoring. "
        "Provides a live SSE stream for env_monitor_streaming and a bulk REST endpoint "
        "for env_monitor_batch to seed its Bronze layer."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(sensors.router, prefix="/v1/sensors", tags=["sensors"])
