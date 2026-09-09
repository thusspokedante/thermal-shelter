import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import climate_service

client = TestClient(app)


def _fake_open_meteo_response():
    return {
        "hourly": {
            "time": ["2026-01-01T00:00", "2026-01-01T01:00"],
            "temperature_2m": [-14.2, -14.8],
            "relative_humidity_2m": [42, 45],
            "wind_speed_10m": [1.8, 2.0],
            "wind_direction_10m": [120, 130],
            "shortwave_radiation": [0, 0],
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


def test_valid_request_returns_normalized_climate_data(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert "latitude" in params and "longitude" in params
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
    data = resp.json()
    assert data["location"] == {"latitude": 34.15, "longitude": 77.58}
    assert len(data["hourly"]) == 2
    first = data["hourly"][0]
    assert first["time"] == "2026-01-01T00:00"
    assert first["temperature"] == -14.2
    assert first["relative_humidity"] == 42
    assert first["wind_speed"] == 1.8
    assert first["wind_direction"] == 120
    assert first["solar_irradiance"] == 0


def test_invalid_coordinates_are_rejected():
    resp = client.get(
        "/api/climate",
        params={
            "latitude": 999,
            "longitude": 77.58,
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
        },
    )
    assert resp.status_code == 422  # FastAPI query validation (ge=-90, le=90)


def test_invalid_date_range_is_rejected(monkeypatch):
    # Should be rejected before any HTTP call is attempted.
    def fake_get(*args, **kwargs):
        raise AssertionError("Open-Meteo should not be called for an invalid date range")

    monkeypatch.setattr(climate_service.httpx, "get", fake_get)

    resp = client.get(
        "/api/climate",
        params={
            "latitude": 34.15,
            "longitude": 77.58,
            "start_date": "2026-01-02",
            "end_date": "2026-01-01",
        },
    )
    assert resp.status_code == 400


def test_external_api_failure_is_handled(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(500, None, text="internal error")

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
    assert resp.status_code == 502


def test_connection_failure_is_handled(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise httpx.ConnectError("boom")

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
    assert resp.status_code == 502


def test_timeout_is_handled(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise httpx.TimeoutException("boom")

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
    assert resp.status_code == 504


def test_malformed_response_is_handled(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(200, {"hourly": {"time": ["2026-01-01T00:00"]}})  # missing fields

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
    assert resp.status_code == 400
