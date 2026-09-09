from app.schemas.simulation import SimulationFromClimateRequest, SimulationRequest
from app.services.climate_service import get_climate, to_climate_points
from app.thermal.solver import simulate

def run_simulation(request: SimulationRequest):
    return simulate(request)


def run_simulation_from_climate(request: SimulationFromClimateRequest):
    """
    Fetch real hourly climate data (existing /api/climate flow) for the given
    location/date range, convert it to ClimatePoint[], then run it through
    the existing thermal simulation exactly as SimulationRequest.climate
    would be used.
    """
    climate_response = get_climate(
        request.latitude, request.longitude, request.start_date, request.end_date
    )
    climate_points = to_climate_points(climate_response.hourly)

    simulation_request = SimulationRequest(
        geometry=request.geometry,
        wall=request.wall,
        roof=request.roof,
        floor=request.floor,
        windows=request.windows,
        doors=request.doors,
        climate=climate_points,
        settings=request.settings,
    )
    return simulate(simulation_request)
