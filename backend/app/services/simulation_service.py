from app.schemas.simulation import (
    ComparisonRequest,
    DesignComparisonMetrics,
    DesignComparisonResult,
    SimulationFromClimateRequest,
    SimulationRequest,
)
from app.services.climate_service import get_climate, to_climate_points
from app.thermal.solver import simulate

def run_simulation(request: SimulationRequest):
    return simulate(request)


def run_comparison(request: ComparisonRequest):
    """
    Simulate every design in the request under the same shared climate
    and settings, using the existing simulate() thermal solver for each
    design, then rank the designs.

    This is a thin layer around the existing simulation engine: it does
    not duplicate any thermal calculations from thermal/solver.py.

    Ranking (prototype rule, intentionally simple):
      1. Higher comfort_hours is better.
      2. Ties broken by lower total_heat_loss_kwh.
    """
    unranked = []

    for design in request.designs:
        simulation_request = SimulationRequest(
            geometry=design.geometry,
            wall=design.wall,
            roof=design.roof,
            floor=design.floor,
            windows=design.windows,
            doors=design.doors,
            climate=request.climate,
            settings=request.settings,
        )
        result = simulate(simulation_request)
        summary = result["summary"]

        metrics = DesignComparisonMetrics(
            minimum_indoor_temperature_c=summary["indoor_temperature_min_c"],
            maximum_indoor_temperature_c=summary["indoor_temperature_max_c"],
            average_indoor_temperature_c=summary["indoor_temperature_average_c"],
            comfort_hours=summary["comfort_hours"],
            solar_energy_captured_kwh=summary["solar_energy_captured_kwh"],
            total_heat_loss_kwh=summary["total_heat_loss_kwh"],
        )

        unranked.append((design.design_id, design.name, metrics))

    ranked = sorted(
        unranked,
        key=lambda item: (-item[2].comfort_hours, item[2].total_heat_loss_kwh),
    )

    results = [
        DesignComparisonResult(
            design_id=design_id,
            name=name,
            rank=rank,
            metrics=metrics,
        )
        for rank, (design_id, name, metrics) in enumerate(ranked, start=1)
    ]

    return {
        "design_count": len(results),
        "recommended_design": results[0].name,
        "results": results,
    }


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
