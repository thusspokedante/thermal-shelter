# Thermal Shelter Simulation Backend

FastAPI backend for the SIH area-specific thermal shelter project.

## What it does

- Accepts shelter geometry, wall/roof/floor material layers, windows, doors and climate data.
- Runs a transient reduced-order thermal simulation.
- Returns indoor temperature over time.
- Calculates solar gains.
- Calculates wall/roof/floor/window/door/infiltration/radiation heat-flow contributions.
- Returns comfort hours and envelope U-values.
- Provides a material catalog, stored in a SQLite database (`materials.db`).
- Is ready to connect to a React/Next/Vite frontend.

## Run

Python 3.11+ recommended.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Install:
```bash
pip install -r requirements.txt
```

## Material database

Materials live in a SQLite file (`materials.db`), created automatically the
first time the app starts. To create/seed it manually instead:

```bash
python seed_db.py
```

This creates the `materials` table (if missing) and inserts the 14 default
materials. It's safe to run again — existing IDs are left untouched.

Start the API:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
(the app also creates/seeds the database automatically on startup, so this
alone is enough for a fresh clone)

Open:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

Test the materials endpoint:
```bash
curl http://localhost:8000/api/materials
curl http://localhost:8000/api/materials/aac
```

Run the automated tests:
```bash
pytest
```

### Adding or updating a material

There's no dedicated write endpoint yet. To add or edit a material, either:
- add/edit an entry in `app/seed_data.py` and re-run `python seed_db.py`
  (existing IDs aren't overwritten by the seed script, so edit the DB row or
  delete `materials.db` and reseed if you need to change an existing value), or
- use `app.services.material_service.add_material(data)` from a Python shell,
  which validates the values and inserts/updates the row directly.

## Frontend request

POST `/api/simulation`

Example body:

```json
{
  "geometry": {
    "length_m": 4,
    "width_m": 4,
    "height_m": 3
  },
  "wall": {
    "layers": [
      {"material_id": "stone", "thickness_m": 0.30},
      {"material_id": "mineral_wool", "thickness_m": 0.08},
      {"material_id": "plaster", "thickness_m": 0.02}
    ]
  },
  "roof": {
    "layers": [
      {"material_id": "concrete", "thickness_m": 0.15},
      {"material_id": "mineral_wool", "thickness_m": 0.10}
    ]
  },
  "floor": {
    "layers": [
      {"material_id": "concrete", "thickness_m": 0.15}
    ]
  },
  "windows": [
    {
      "area_m2": 2,
      "u_value_w_m2k": 1.8,
      "shgc": 0.60,
      "solar_exposure_factor": 1.0
    }
  ],
  "doors": [
    {
      "area_m2": 2,
      "u_value_w_m2k": 1.5,
      "shgc": 0,
      "solar_exposure_factor": 0
    }
  ],
  "settings": {
    "duration_hours": 24,
    "timestep_minutes": 10,
    "initial_indoor_temperature_c": 20,
    "air_changes_per_hour": 0.3,
    "indoor_heat_gain_w": 100,
    "comfort_min_c": 18,
    "comfort_max_c": 27
  },
  "climate": [
    {
      "timestamp": "2026-01-01T00:00:00",
      "outdoor_temperature_c": -10,
      "solar_irradiance_w_m2": 0,
      "relative_humidity_percent": 40,
      "wind_speed_m_s": 2
    },
    {
      "timestamp": "2026-01-01T01:00:00",
      "outdoor_temperature_c": -11,
      "solar_irradiance_w_m2": 0,
      "relative_humidity_percent": 40,
      "wind_speed_m_s": 2
    }
  ]
}
```

The climate array should normally contain a full time series matching the simulation period. The solver interpolates it to the requested timestep.

## Important engineering note

This is the backend foundation, not a certified building-energy simulation package and not a replacement for ANSYS. Before using numerical results in the SIH final presentation, benchmark the reduced-order solver against ANSYS and/or experimental data and replace the example material properties with verified sources.

## Suggested next upgrades

1. Real Open-Meteo/NASA POWER climate ingestion.
2. Solar position/orientation/shading model.
3. Multi-node wall thermal model.
4. PCM thermal storage.
5. Ground coupling.
6. Material database with sources and uncertainty.
7. Design optimization endpoint.
8. ANSYS benchmark import/comparison.
9. Authentication and persistent simulation history.
