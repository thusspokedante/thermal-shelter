"""
Tests for the climate -> simulation integration:
  - Converting ClimateHourlyPoint[] (from /api/climate) into ClimatePoint[]
    (expected by the thermal solver).
  - Running the existing simulation with a converted climate series.
  - The new POST /api/simulation/from-climate endpoint, which fetches
    climate data and feeds it into the existing simulation in one call.

The real Open-Meteo service is never contacted; httpx.get is monkeypatched,
same pattern as tests/test_climate.py.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.climate import ClimateHourlyPoint
from app.services import climate_service
from app.services.climate_service import to_climate_points

client = TestClient(app)


def _fake_open_meteo_response():
    return {
        "hourly": {
            "time": [
                "2026-01-01T00:00",
                "2026-01-01T01:00",
                "2026-01-01T02:00",
            ],
            "temperature_2m": [-6.3, -6.8, -7.1],
            "relative_humidity_2m": [48, 50, 52],
            "wind_speed_10m": [0.91, 1.10, 1.20],
            "wind_direction_10m": [6, 10, 12],
            "shortwave_radiation": [0, 0, 0],
        }
    }


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


def _sample_construction():
    return {"layers": [{"material_id": "brick", "thickness_m": 0.2}]}


def _sample_simulation_body(**overrides):
    body = {
        "geometry": {"length_m": 4, "width_m": 4, "height_m": 3},
        "wall": _sample_construction(),
        "roof": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "floor": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "windows": [],
        "doors": [],
        "settings": {
            "duration_hours": 2,
            "timestep_minutes": 30,
            "initial_indoor_temperature_c": 20,
        },
    }
    body.update(overrides)
    return body


# 1. Conversion: ClimateHourlyPoint[] -> ClimatePoint[]

def test_to_climate_points_maps_fields_correctly():
    hourly = [
        ClimateHourlyPoint(
            time="2026-01-01T00:00",
            temperature=-6.3,
            relative_humidity=48,
            wind_speed=0.91,
            wind_direction=6,
            solar_irradiance=0,
        ),
        ClimateHourlyPoint(
            time="2026-01-01T01:00",
            temperature=-6.8,
            relative_humidity=50,
            wind_speed=1.10,
            wind_direction=10,
            solar_irradiance=0,
        ),
    ]

    points = to_climate_points(hourly)

    assert len(points) == 2
    first = points[0]
    assert first.timestamp == "2026-01-01T00:00"
    assert first.outdoor_temperature_c == -6.3
    assert first.relative_humidity_percent == 48
    assert first.wind_speed_m_s == 0.91
    assert first.solar_irradiance_w_m2 == 0


# 2. A converted climate series can be passed into the existing simulation.

def test_converted_climate_series_runs_through_existing_simulation():
    hourly = [
        ClimateHourlyPoint(
            time=f"2026-01-01T0{i}:00",
            temperature=10.0 - i,
            relative_humidity=40,
            wind_speed=2.0,
            wind_direction=0,
            solar_irradiance=0,
        )
        for i in range(3)
    ]
    points = to_climate_points(hourly)

    body = _sample_simulation_body(
        climate=[
            {
                "timestamp": p.timestamp,
                "outdoor_temperature_c": p.outdoor_temperature_c,
                "solar_irradiance_w_m2": p.solar_irradiance_w_m2,
                "relative_humidity_percent": p.relative_humidity_percent,
                "wind_speed_m_s": p.wind_speed_m_s,
            }
            for p in points
        ]
    )

    resp = client.post("/api/simulation", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "indoor_temperature_average_c" in data["summary"]


# 3. New combined endpoint: location + date range -> simulation results.

def test_simulation_from_climate_returns_valid_thermal_results(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "latitude" in params and "longitude" in params
        return _FakeResponse(200, _fake_open_meteo_response())

    monkeypatch.setattr(climate_service.httpx, "get", fake_get)

    body = _sample_simulation_body(
        latitude=34.15,
        longitude=77.58,
        start_date="2026-01-01",
        end_date="2026-01-02",
    )

    resp = client.post("/api/simulation/from-climate", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "time_series" in data
    assert len(data["time_series"]) > 0
    assert "indoor_temperature_min_c" in data["summary"]
    assert "solar_energy_captured_kwh" in data["summary"]


def test_simulation_from_climate_propagates_open_meteo_errors(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(500, None, text="internal error")

    monkeypatch.setattr(climate_service.httpx, "get", fake_get)

    body = _sample_simulation_body(
        latitude=34.15,
        longitude=77.58,
        start_date="2026-01-01",
        end_date="2026-01-02",
    )

    resp = client.post("/api/simulation/from-climate", json=body)
    assert resp.status_code == 502


# 4. Existing endpoints/tests are unaffected (sanity checks; full suites
#    live in test_climate.py and test_materials.py).

def test_existing_climate_endpoint_still_works(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(200, _fake_open_meteo_response())

    monkeypatch.setattr(climate_service.httpx, "get", fake_get)

    resp = client.get(
        "/api/climate",
        params={
            "latitude": 34.15,
            "longitude": 77.58,
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["hourly"]) == 3


def test_existing_simulation_endpoint_still_works():
    body = _sample_simulation_body(
        climate=[
            {"timestamp": "2026-01-01T00:00:00", "outdoor_temperature_c": 10,
             "solar_irradiance_w_m2": 0, "relative_humidity_percent": 40,
             "wind_speed_m_s": 2},
            {"timestamp": "2026-01-01T01:00:00", "outdoor_temperature_c": 9,
             "solar_irradiance_w_m2": 0, "relative_humidity_percent": 40,
             "wind_speed_m_s": 2},
        ]
    )
    resp = client.post("/api/simulation", json=body)
    assert resp.status_code == 200
