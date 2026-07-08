import unittest
from httpx import AsyncClient, ASGITransport

from app.main import app

VALID_RISK_LEVELS = {"LOW", "MODERATE", "HIGH", "CRITICAL"}
VALID_ZONE_IDS = {"zone-a", "zone-b", "zone-c", "zone-d"}


class TestHealth(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_health_returns_ok(self):
        response = await self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    async def test_health_includes_version(self):
        response = await self.client.get("/health")
        self.assertIn("version", response.json())


class TestSensorList(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_returns_12_sensors(self):
        response = await self.client.get("/v1/sensors")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 12)

    async def test_sensor_has_required_fields(self):
        response = await self.client.get("/v1/sensors")
        sensor = response.json()[0]
        for field in ("sensor_id", "zone_id", "zone_name", "latitude", "longitude", "active"):
            self.assertIn(field, sensor)

    async def test_all_zones_represented(self):
        response = await self.client.get("/v1/sensors")
        zones = {s["zone_id"] for s in response.json()}
        self.assertEqual(zones, VALID_ZONE_IDS)


class TestCurrentReadings(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_returns_one_reading_per_sensor(self):
        response = await self.client.get("/v1/sensors/readings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 12)

    async def test_reading_fields_present(self):
        response = await self.client.get("/v1/sensors/readings")
        reading = response.json()[0]
        for field in (
            "sensor_id", "zone_id", "zone_name", "timestamp",
            "temperature_f", "humidity_pct", "wind_speed_mph",
            "pm25_ugm3", "battery_pct", "latitude", "longitude", "wildfire_risk",
        ):
            self.assertIn(field, reading)

    async def test_wildfire_risk_is_valid(self):
        response = await self.client.get("/v1/sensors/readings")
        for reading in response.json():
            self.assertIn(reading["wildfire_risk"], VALID_RISK_LEVELS)

    async def test_numeric_fields_in_range(self):
        response = await self.client.get("/v1/sensors/readings")
        for r in response.json():
            self.assertGreaterEqual(r["humidity_pct"], 0)
            self.assertLessEqual(r["humidity_pct"], 100)
            self.assertGreaterEqual(r["wind_speed_mph"], 0)
            self.assertGreaterEqual(r["pm25_ugm3"], 0)
            self.assertGreaterEqual(r["battery_pct"], 0)
            self.assertLessEqual(r["battery_pct"], 100)


class TestBulkReadings(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_default_params(self):
        response = await self.client.get("/v1/sensors/readings/bulk")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["interval_seconds"], 300)
        self.assertEqual(data["sensor_count"], 12)
        self.assertGreater(data["reading_count"], 0)
        self.assertEqual(len(data["readings"]), data["reading_count"])

    async def test_zone_filter(self):
        response = await self.client.get("/v1/sensors/readings/bulk?zone_id=zone-a&hours=1&interval_seconds=3600")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(all(r["zone_id"] == "zone-a" for r in data["readings"]))
        self.assertEqual(data["sensor_count"], 3)

    async def test_hours_too_large_rejected(self):
        response = await self.client.get("/v1/sensors/readings/bulk?hours=8761")
        self.assertEqual(response.status_code, 422)

    async def test_interval_too_small_rejected(self):
        response = await self.client.get("/v1/sensors/readings/bulk?interval_seconds=10")
        self.assertEqual(response.status_code, 422)

    async def test_reading_count_matches_expected(self):
        response = await self.client.get("/v1/sensors/readings/bulk?hours=1&interval_seconds=3600")
        data = response.json()
        # 1 hour at 60-min intervals = 2 time slots (start and end), 12 sensors each
        self.assertGreaterEqual(data["reading_count"], 12)


class TestBulkReadingsDateRange(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_explicit_start_and_end_reflected_in_response(self):
        response = await self.client.get(
            "/v1/sensors/readings/bulk"
            "?start=2026-07-01T00:00:00Z&end=2026-07-01T06:00:00Z&interval_seconds=3600"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("2026-07-01T00:00:00", data["start"])
        self.assertIn("2026-07-01T06:00:00", data["end"])

    async def test_explicit_start_and_end_reading_count(self):
        # 6-hour window at 1-hour intervals: timestamps 00:00..06:00 inclusive = 7 slots × 12 sensors
        response = await self.client.get(
            "/v1/sensors/readings/bulk"
            "?start=2026-07-01T00:00:00Z&end=2026-07-01T06:00:00Z&interval_seconds=3600"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reading_count"], 7 * 12)

    async def test_start_takes_precedence_over_hours(self):
        # hours=24 should be ignored when start is provided
        with_hours = await self.client.get(
            "/v1/sensors/readings/bulk"
            "?start=2026-07-01T00:00:00Z&end=2026-07-01T01:00:00Z&hours=24&interval_seconds=3600"
        )
        without_hours = await self.client.get(
            "/v1/sensors/readings/bulk"
            "?start=2026-07-01T00:00:00Z&end=2026-07-01T01:00:00Z&interval_seconds=3600"
        )
        self.assertEqual(with_hours.status_code, 200)
        self.assertEqual(
            with_hours.json()["reading_count"],
            without_hours.json()["reading_count"],
        )

    async def test_end_without_start_falls_back_to_hours(self):
        # Providing only end: start should be end minus 24 hours (default hours=24)
        response = await self.client.get(
            "/v1/sensors/readings/bulk?end=2026-07-01T12:00:00Z&interval_seconds=3600"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("2026-07-01T12:00:00", data["end"])
        self.assertIn("2026-06-30T12:00:00", data["start"])

    async def test_naive_datetime_treated_as_utc(self):
        response = await self.client.get(
            "/v1/sensors/readings/bulk"
            "?start=2026-07-01T00:00:00&end=2026-07-01T01:00:00&interval_seconds=3600"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data["reading_count"], 0)
        self.assertIn("2026-07-01T00:00:00", data["start"])

    async def test_start_after_end_returns_empty_readings(self):
        response = await self.client.get(
            "/v1/sensors/readings/bulk"
            "?start=2026-07-01T06:00:00Z&end=2026-07-01T00:00:00Z&interval_seconds=3600"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reading_count"], 0)


if __name__ == "__main__":
    unittest.main()
