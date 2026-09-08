from fastapi import APIRouter, HTTPException
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services.simulation_service import run_simulation

router = APIRouter(tags=["simulation"])

@router.post("/simulation", response_model=SimulationResponse)
def simulate(request: SimulationRequest):
    try:
        return run_simulation(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")
