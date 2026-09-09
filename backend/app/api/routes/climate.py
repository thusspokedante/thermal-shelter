from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.climate import ClimatePoint, ClimateResponse
from app.services.climate_service import get_climate

router = APIRouter(tags=["climate"])

@router.post("/climate/validate")
def validate_climate(data: list[ClimatePoint]):
    return {"valid": True, "points": len(data)}


@router.get("/climate", response_model=ClimateResponse)
def fetch_climate(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD), historical"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD), historical"),
):
    """
    Fetch historical hourly climate data for a location from Open-Meteo and
    return it normalized for use by the thermal simulation.
    """
    try:
        return get_climate(latitude, longitude, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except ConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
