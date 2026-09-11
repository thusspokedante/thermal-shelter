from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.schemas.climate import ClimatePoint

class MaterialLayer(BaseModel):
    material_id: str
    thickness_m: float = Field(gt=0)

class SurfaceConstruction(BaseModel):
    layers: list[MaterialLayer] = Field(min_length=1)

class Geometry(BaseModel):
    length_m: float = Field(default=4.0, gt=0)
    width_m: float = Field(default=4.0, gt=0)
    height_m: float = Field(default=3.0, gt=0)

class Opening(BaseModel):
    area_m2: float = Field(gt=0)
    u_value_w_m2k: float = Field(gt=0)
    shgc: float = Field(default=0.0, ge=0, le=1)
    solar_exposure_factor: float = Field(default=1.0, ge=0, le=1)

class SimulationSettings(BaseModel):
    duration_hours: float = Field(default=24.0, gt=0, le=168)
    timestep_minutes: int = Field(default=10, ge=1, le=60)
    initial_indoor_temperature_c: float = 20.0
    air_changes_per_hour: float = Field(default=0.3, ge=0)
    indoor_heat_gain_w: float = Field(default=100.0, ge=0)
    comfort_min_c: float = 18.0
    comfort_max_c: float = 27.0

class SimulationRequest(BaseModel):
    geometry: Geometry = Geometry()
    wall: SurfaceConstruction
    roof: SurfaceConstruction
    floor: SurfaceConstruction
    windows: list[Opening] = []
    doors: list[Opening] = []
    climate: list[ClimatePoint]
    settings: SimulationSettings = SimulationSettings()

    @model_validator(mode="after")
    def check_climate(self):
        if len(self.climate) < 2:
            raise ValueError("At least two climate points are required.")
        return self

class SimulationResponse(BaseModel):
    summary: dict
    time_series: list[dict]
    heat_loss_breakdown: dict
    assumptions: list[str]

class ShelterDesign(BaseModel):
    """
    A single named shelter design to be simulated as part of a
    multi-design comparison. Mirrors the design-relevant fields of
    SimulationRequest (geometry/wall/roof/floor/windows/doors), but
    deliberately omits climate/settings since those are shared across
    every design in a ComparisonRequest.
    """
    design_id: str
    name: str
    geometry: Geometry = Geometry()
    wall: SurfaceConstruction
    roof: SurfaceConstruction
    floor: SurfaceConstruction
    windows: list[Opening] = []
    doors: list[Opening] = []


class ComparisonRequest(BaseModel):
    designs: list[ShelterDesign] = Field(min_length=2)
    climate: list[ClimatePoint]
    settings: SimulationSettings = SimulationSettings()

    @model_validator(mode="after")
    def check_climate(self):
        if len(self.climate) < 2:
            raise ValueError("At least two climate points are required.")
        return self


class DesignComparisonMetrics(BaseModel):
    minimum_indoor_temperature_c: float
    maximum_indoor_temperature_c: float
    average_indoor_temperature_c: float
    comfort_hours: float
    solar_energy_captured_kwh: float
    total_heat_loss_kwh: float


class DesignComparisonResult(BaseModel):
    design_id: str
    name: str
    rank: int
    metrics: DesignComparisonMetrics


class ComparisonResponse(BaseModel):
    design_count: int
    recommended_design: str
    results: list[DesignComparisonResult]


class SimulationFromClimateRequest(BaseModel):
    """
    Same as SimulationRequest, but instead of supplying a pre-built climate
    series, the caller supplies a location + date range. Real hourly climate
    data is fetched from Open-Meteo (via the existing /api/climate flow) and
    converted into ClimatePoint[] before running the same thermal solver.
    """
    geometry: Geometry = Geometry()
    wall: SurfaceConstruction
    roof: SurfaceConstruction
    floor: SurfaceConstruction
    windows: list[Opening] = []
    doors: list[Opening] = []
    settings: SimulationSettings = SimulationSettings()

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_date: date
    end_date: date
