from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

EXPECTED_IDS = {
    "stone", "concrete", "brick", "aac", "rammed_earth", "wood", "plywood",
    "mineral_wool", "glass_wool", "eps_insulation", "xps_insulation",
    "polyurethane", "plaster", "glass",
}

REQUIRED_FIELDS = {
    "id", "name", "thermal_conductivity_w_mk", "density_kg_m3",
    "specific_heat_j_kgk", "solar_absorptance",
}


def test_materials_list_has_all_14():
    resp = client.get("/api/materials")
    assert resp.status_code == 200
    materials = resp.json()["materials"]
    ids = {m["id"] for m in materials}
    assert ids == EXPECTED_IDS


def test_material_fields_present_and_valid():
    resp = client.get("/api/materials")
    for m in resp.json()["materials"]:
        assert REQUIRED_FIELDS.issubset(m.keys())
        assert m["thermal_conductivity_w_mk"] > 0
        assert m["density_kg_m3"] > 0
        assert m["specific_heat_j_kgk"] > 0
        assert 0 <= m["solar_absorptance"] <= 1


def test_existing_material_ids_still_work():
    for material_id in ["stone", "concrete", "brick", "mineral_wool",
                         "eps_insulation", "plaster", "wood", "glass"]:
        resp = client.get(f"/api/materials/{material_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == material_id


def test_unknown_material_returns_404():
    resp = client.get("/api/materials/unobtanium")
    assert resp.status_code == 404


def test_simulation_still_runs_with_db_materials():
    body = {
        "geometry": {"length_m": 4, "width_m": 4, "height_m": 3},
        "wall": {"layers": [{"material_id": "brick", "thickness_m": 0.2}]},
        "roof": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "floor": {"layers": [{"material_id": "concrete", "thickness_m": 0.15}]},
        "windows": [],
        "doors": [],
        "settings": {
            "duration_hours": 2,
            "timestep_minutes": 30,
            "initial_indoor_temperature_c": 20,
        },
        "climate": [
            {"timestamp": "2026-01-01T00:00:00", "outdoor_temperature_c": 10,
             "solar_irradiance_w_m2": 0, "relative_humidity_percent": 40,
             "wind_speed_m_s": 2},
            {"timestamp": "2026-01-01T01:00:00", "outdoor_temperature_c": 9,
             "solar_irradiance_w_m2": 0, "relative_humidity_percent": 40,
             "wind_speed_m_s": 2},
            {"timestamp": "2026-01-01T02:00:00", "outdoor_temperature_c": 8,
             "solar_irradiance_w_m2": 0, "relative_humidity_percent": 40,
             "wind_speed_m_s": 2},
        ],
    }
    resp = client.post("/api/simulation", json=body)
    assert resp.status_code == 200
    assert "summary" in resp.json()
