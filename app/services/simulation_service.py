from app.schemas.simulation import SimulationRequest
from app.thermal.solver import simulate

def run_simulation(request: SimulationRequest):
    return simulate(request)
