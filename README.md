# Thermal Shelter Simulation

Software-based model for designing area-specific shelters for thermal
comfort maintenance. A FastAPI backend runs a reduced-order transient
thermal simulation (indoor temperature, heat flow, solar gain, comfort
hours) for a shelter built from a material catalog stored in SQLite, driven
by either a custom climate series or real historical weather data.

## First-time setup (Windows)

```bat
git clone <repo-url>
cd thermal-shelter
setup.bat
```

`setup.bat` creates `.venv` at the project root (outside `backend/`),
installs `backend/requirements.txt`, and seeds the SQLite material
database. It's safe to re-run — it won't recreate an existing `.venv` or
duplicate materials in an already-seeded database.

## Running the backend

```bat
run.bat
```

Starts the FastAPI app at `http://127.0.0.1:8000`. Swagger UI (interactive
API docs) is at `http://127.0.0.1:8000/docs`.

## Running tests

```bat
.venv\Scripts\python.exe -m pytest backend\tests -v
```

(or `cd backend`, activate `..\.venv`, and run `pytest`)

## Climate API

`GET /api/climate` fetches historical hourly weather for a location from
[Open-Meteo](https://open-meteo.com) and returns it normalized:

```
GET /api/climate?latitude=34.15&longitude=77.58&start_date=2026-01-01&end_date=2026-01-02
```

## Climate → simulation flow

- `POST /api/simulation` runs the thermal solver on a climate series you
  provide directly (`ClimatePoint[]`).
- `POST /api/simulation/from-climate` does the same, but instead of a
  climate series you give a `latitude`, `longitude`, `start_date`, and
  `end_date`. It fetches hourly data from Open-Meteo, converts it into the
  `ClimatePoint[]` format the solver expects, and returns the same thermal
  results (indoor temperature, heat flow, solar energy, comfort hours).

Both endpoints, and `/api/materials`, are documented and testable at
`/docs`.

See `backend/README.md` for full request/response details.
