# env_monitor_api

Mock IoT sensor data generator for the Smart City Wildfire & Environmental Monitoring system. This service is the data source for the two downstream pipelines:

| Consumer | Endpoint | Purpose |
|---|---|---|
| `env_monitor_streaming` | `GET /v1/sensors/stream` | SSE stream of live readings → Kafka |
| `env_monitor_batch` | `GET /v1/sensors/readings/bulk` | Historical bulk data → Bronze layer files |

## Sensors

12 solar-powered IoT sensors across 4 zones in a high-risk forest area:

| Zone | Name | Sensors |
|---|---|---|
| `zone-a` | Northern Forest Ridge | SNS-001, SNS-002, SNS-003 |
| `zone-b` | Southern Valley Floor | SNS-004, SNS-005, SNS-006 |
| `zone-c` | Eastern Canyon | SNS-007, SNS-008, SNS-009 |
| `zone-d` | Western Meadow | SNS-010, SNS-011, SNS-012 |

Each reading includes: `temperature_f`, `humidity_pct`, `wind_speed_mph`, `pm25_ugm3`, `battery_pct`, `latitude`, `longitude`, and a derived `wildfire_risk` level (`LOW` / `MODERATE` / `HIGH` / `CRITICAL`).

Wildfire events are zone-correlated and autocorrelated across time: once a fire event starts in a zone, it persists across intervals with an 80% carry-forward probability.

## Endpoints

```
GET /health                          Health check
GET /v1/sensors                      List sensor metadata
GET /v1/sensors/readings             Current snapshot (one reading per sensor)
GET /v1/sensors/readings/bulk        Historical bulk data
GET /v1/sensors/stream               SSE live stream
```

### Bulk query parameters

| Param | Default | Range | Description |
|---|---|---|---|
| `hours` | 24 | 1–72 | Hours of history to generate |
| `interval_seconds` | 300 | 60–3600 | Seconds between readings per sensor |
| `zone_id` | — | zone-a…zone-d | Filter to one zone |

### SSE event format

```
event: sensor_reading
data: {"sensor_id":"SNS-001","zone_id":"zone-a","timestamp":"...","temperature_f":82.4,...}

: keepalive
```

Events are emitted every `STREAM_INTERVAL_SECONDS` seconds (default 5). A keepalive comment is sent every 3 cycles to prevent proxy timeouts.

## Running locally

```bash
cp .env.example .env
python -m venv env_monitor_api
source env_monitor_api/bin/activate        # Windows: env_monitor_api\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs

## Running with Docker

```bash
docker compose up --build
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `STREAM_INTERVAL_SECONDS` | `5.0` | Seconds between SSE emission cycles |
| `WILDFIRE_EVENT_PROBABILITY` | `0.05` | Per-zone probability of a fire event starting each cycle |
| `BULK_MAX_HOURS` | `72` | Maximum hours allowed for bulk requests |

## Tests

```bash
python -m unittest discover tests
```

## Project structure

```
app/
├── core/config.py          # Pydantic Settings
├── models/sensor.py        # SensorReading, SensorMeta, BulkReadingsResponse
├── services/simulator.py   # Data generation and fire event logic
├── routers/
│   ├── health.py           # GET /health
│   └── sensors.py          # All /v1/sensors/* routes
└── main.py                 # FastAPI app
tests/
└── test_sensors.py         # unittest suite
```
