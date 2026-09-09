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

## Climate API

`GET /api/climate` fetches historical hourly weather for a location from the
free [Open-Meteo](https://open-meteo.com) archive API and returns it
normalized (not Open-Meteo's raw response), for later use by the thermal
simulation. Data is fetched on demand — nothing is cached or stored in
SQLite yet.

Query parameters:

| Parameter    | Type   | Description                              |
|--------------|--------|-------------------------------------------|
| `latitude`   | float  | -90 to 90                                  |
| `longitude`  | float  | -180 to 180                                |
| `start_date` | date   | `YYYY-MM-DD`, historical                   |
| `end_date`   | date   | `YYYY-MM-DD`, historical, on/after start   |

Units: temperature in °C, wind speed in m/s, solar irradiance
(shortwave/global horizontal) in W/m², relative humidity in %.

Example request:
```bash
curl "http://localhost:8000/api/climate?latitude=34.15&longitude=77.58&start_date=2026-01-01&end_date=2026-01-02"
```

Example response (truncated):
```json
{
  "location": { "latitude": 34.15, "longitude": 77.58 },
  "hourly": [
    {
      "time": "2026-01-01T00:00",
      "temperature": -14.2,
      "relative_humidity": 42,
      "wind_speed": 1.8,
      "wind_direction": 120,
      "solar_irradiance": 0
    }
  ]
}
```

Errors: invalid coordinates or an invalid date range return `400`; Open-Meteo
HTTP/API errors return `502`; a request timeout returns `504`.

Run just the climate tests (they mock the Open-Meteo HTTP call, no network
needed):
```bash
pytest tests/test_climate.py -v
```

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

### Running the simulation from real climate data

`POST /api/simulation/from-climate` accepts the same body as `/api/simulation`
except that `climate` is replaced with `latitude`, `longitude`, `start_date`,
and `end_date`. It fetches hourly data from Open-Meteo (the same flow as
`GET /api/climate`), converts it into `ClimatePoint[]`, and runs it through
the same thermal solver:

```json
{
  "geometry": { "length_m": 4, "width_m": 4, "height_m": 3 },
  "wall": { "layers": [{ "material_id": "stone", "thickness_m": 0.30 }] },
  "roof": { "layers": [{ "material_id": "concrete", "thickness_m": 0.15 }] },
  "floor": { "layers": [{ "material_id": "concrete", "thickness_m": 0.15 }] },
  "windows": [],
  "doors": [],
  "settings": { "duration_hours": 24, "timestep_minutes": 10 },
  "latitude": 34.15,
  "longitude": 77.58,
  "start_date": "2026-01-01",
  "end_date": "2026-01-02"
}
```

Errors from the Open-Meteo fetch (bad coordinates, timeout, upstream
failure) surface with the same status codes as `GET /api/climate`
(`400`/`502`/`504`).

## Important engineering note

This is the backend foundation, not a certified building-energy simulation package and not a replacement for ANSYS. Before using numerical results in the SIH final presentation, benchmark the reduced-order solver against ANSYS and/or experimental data and replace the example material properties with verified sources.

## Suggested next upgrades

1. Climate data caching/storage, and NASA POWER as a fallback provider.
2. Solar position/orientation/shading model.
3. Multi-node wall thermal model.
4. PCM thermal storage.
5. Ground coupling.
6. Material database with sources and uncertainty.
7. Design optimization endpoint.
8. ANSYS benchmark import/comparison.
9. Authentication and persistent simulation history.
