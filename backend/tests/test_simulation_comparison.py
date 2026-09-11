"""
Tests for the multi-design comparison feature:
  - POST /api/simulation/compare

The comparison endpoint is a thin layer around the existing thermal
simulation engine (app.thermal.solver.simulate): every design is run
through the same simulate() call used by POST /api/simulation, under
shared climate/settings, and the results are ranked.

No external services are involved, so no network mocking is needed
here (unlike test_climate_simulation_integration.py).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _construction(material_id="brick", thickness_m=0.2):
    return {"layers": [{"material_id": material_id, "thickness_m": thickness_m}]}


def _shared_climate(hours=2):
    return [
        {
            "timestamp": f"2026-01-01T0{i}:00:00",
            "outdoor_temperature_c": -5.0 - i,
            "solar_irradiance_w_m2": 0,
            "relative_humidity_percent": 40,
            "wind_speed_m_s": 2,
        }
        for i in range(hours)
    ]


def _shared_settings(**overrides):
    settings = {
        "duration_hours": 1,
        "timestep_minutes": 30,
        "initial_indoor_temperature_c": 20,
    }
    settings.update(overrides)
    return settings


def _design(design_id, name, **overrides):
    design = {
        "design_id": design_id,
        "name": name,
        "geometry": {"length_m": 4, "width_m": 4, "height_m": 3},
        "wall": _construction(),
        "roof": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "floor": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "windows": [],
        "doors": [],
    }
    design.update(overrides)
    return design


def _comparison_body(designs, **overrides):
    body = {
        "designs": designs,
        "climate": _shared_climate(),
        "settings": _shared_settings(),
    }
    body.update(overrides)
    return body


# 1. Fewer than 2 designs is rejected.

def test_single_design_is_rejected():
    body = _comparison_body([_design("A", "Design A")])
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 422


def test_zero_designs_is_rejected():
    body = _comparison_body([])
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 422


# 2. Two or more designs can be compared.

def test_two_designs_can_be_compared():
    body = _comparison_body(
        [
            _design("A", "Design A"),
            _design(
                "B",
                "Design B",
                wall={"layers": [{"material_id": "mineral_wool", "thickness_m": 0.15}]},
            ),
        ]
    )
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["design_count"] == 2


def test_three_designs_can_be_compared():
    body = _comparison_body(
        [
            _design("A", "Design A"),
            _design("B", "Design B"),
            _design("C", "Design C"),
        ]
    )
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 200
    assert resp.json()["design_count"] == 3


# 3. Every design produces a result, and every result has the
#    required metrics.

REQUIRED_METRIC_FIELDS = {
    "minimum_indoor_temperature_c",
    "maximum_indoor_temperature_c",
    "average_indoor_temperature_c",
    "comfort_hours",
    "solar_energy_captured_kwh",
    "total_heat_loss_kwh",
}


def test_every_design_produces_a_result_with_required_metrics():
    body = _comparison_body(
        [
            _design("A", "Design A"),
            _design(
                "B",
                "Design B",
                wall={"layers": [{"material_id": "mineral_wool", "thickness_m": 0.15}]},
            ),
        ]
    )
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["results"]) == 2
    result_ids = {r["design_id"] for r in data["results"]}
    assert result_ids == {"A", "B"}

    for result in data["results"]:
        assert REQUIRED_METRIC_FIELDS.issubset(result["metrics"].keys())


# 4. Ranks are assigned, and recommended_design is returned.

def test_ranks_are_assigned_and_recommended_design_is_returned():
    body = _comparison_body(
        [
            _design("A", "Design A"),
            _design(
                "B",
                "Design B",
                wall={"layers": [{"material_id": "mineral_wool", "thickness_m": 0.15}]},
            ),
        ]
    )
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()

    ranks = sorted(r["rank"] for r in data["results"])
    assert ranks == [1, 2]

    recommended = data["recommended_design"]
    names = {r["name"] for r in data["results"]}
    assert recommended in names

    rank_one = next(r for r in data["results"] if r["rank"] == 1)
    assert rank_one["name"] == recommended


def test_ranking_prefers_higher_comfort_hours_then_lower_heat_loss():
    # Well-insulated wall (mineral_wool) should hold comfortable indoor
    # temperatures better than a poorly-insulated one (glass) under the
    # same cold climate, so it should rank first.
    body = _comparison_body(
        [
            _design(
                "poor",
                "Poorly Insulated",
                wall={"layers": [{"material_id": "glass", "thickness_m": 0.02}]},
            ),
            _design(
                "good",
                "Well Insulated",
                wall={"layers": [{"material_id": "mineral_wool", "thickness_m": 0.2}]},
            ),
        ],
        settings=_shared_settings(duration_hours=1, timestep_minutes=30),
    )
    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()

    by_id = {r["design_id"]: r for r in data["results"]}
    good = by_id["good"]["metrics"]
    poor = by_id["poor"]["metrics"]

    if good["comfort_hours"] != poor["comfort_hours"]:
        better_id = "good" if good["comfort_hours"] > poor["comfort_hours"] else "poor"
    else:
        better_id = (
            "good"
            if good["total_heat_loss_kwh"] <= poor["total_heat_loss_kwh"]
            else "poor"
        )

    assert by_id[better_id]["rank"] == 1


# 5. All designs use the same climate/settings (verified by construction:
#    the comparison request only accepts one climate/settings block, and
#    each simulated design must reflect that shared climate).

def test_all_designs_use_the_same_shared_climate_and_settings():
    shared_climate = _shared_climate(hours=2)
    shared_settings = _shared_settings(duration_hours=1, timestep_minutes=30)

    body = _comparison_body(
        [_design("A", "Design A"), _design("B", "Design B")],
        climate=shared_climate,
        settings=shared_settings,
    )

    # The request schema itself has no per-design climate/settings fields;
    # confirm the payload we send has exactly one shared block, then check
    # that both designs' results were computed over the same duration.
    assert "climate" not in body["designs"][0]
    assert "settings" not in body["designs"][0]

    resp = client.post("/api/simulation/compare", json=body)
    assert resp.status_code == 200
    data = resp.json()

    # Run each design individually through the existing /api/simulation
    # endpoint with the same shared climate/settings, and confirm the
    # comparison metrics match exactly (same climate/settings were used).
    for design_id, design_name in [("A", "Design A"), ("B", "Design B")]:
        design_body = {
            "geometry": {"length_m": 4, "width_m": 4, "height_m": 3},
            "wall": _construction(),
            "roof": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
            "floor": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
            "windows": [],
            "doors": [],
            "climate": shared_climate,
            "settings": shared_settings,
        }
        individual_resp = client.post("/api/simulation", json=design_body)
        assert individual_resp.status_code == 200
        individual_summary = individual_resp.json()["summary"]

        compared_metrics = next(
            r["metrics"] for r in data["results"] if r["design_id"] == design_id
        )
        assert compared_metrics["average_indoor_temperature_c"] == (
            individual_summary["indoor_temperature_average_c"]
        )
        assert compared_metrics["total_heat_loss_kwh"] == (
            individual_summary["total_heat_loss_kwh"]
        )




# 7. Existing simulation tests/endpoints continue to work (sanity check;
#    the full suites live in their own test files).

def test_existing_simulation_endpoint_still_works():
    body = {
        "geometry": {"length_m": 4, "width_m": 4, "height_m": 3},
        "wall": _construction(),
        "roof": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "floor": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "windows": [],
        "doors": [],
        "climate": _shared_climate(),
        "settings": _shared_settings(),
    }
    resp = client.post("/api/simulation", json=body)
    assert resp.status_code == 200
    assert "summary" in resp.json()
