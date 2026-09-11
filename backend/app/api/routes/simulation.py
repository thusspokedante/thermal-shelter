from fastapi import APIRouter, HTTPException
from app.schemas.simulation import (
    ComparisonRequest,
    ComparisonResponse,
    SimulationFromClimateRequest,
    SimulationRequest,
    SimulationResponse,
)
from app.services.simulation_service import (
    run_comparison,
    run_simulation,
    run_simulation_from_climate,
)

router = APIRouter(tags=["simulation"])

@router.post("/simulation", response_model=SimulationResponse)
def simulate(request: SimulationRequest):
    try:
        return run_simulation(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")


@router.post("/simulation/compare", response_model=ComparisonResponse)
def compare_simulations(request: ComparisonRequest):
    """
    Simulate 2+ shelter designs under the exact same shared climate data
    and simulation settings, using the existing simulation engine for
    each design, then rank them and return the recommended design.
    """
    try:
        return run_comparison(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")


@router.post("/simulation/from-climate", response_model=SimulationResponse)
def simulate_from_climate(request: SimulationFromClimateRequest):
    """
    Same thermal simulation as POST /simulation, but the climate series is
    fetched from Open-Meteo for the given location/date range instead of
    being supplied directly in the request body.
    """
    try:
        return run_simulation_from_climate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except ConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")
