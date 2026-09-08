from pydantic import BaseModel, Field

class ClimatePoint(BaseModel):
    timestamp: str
    outdoor_temperature_c: float
    solar_irradiance_w_m2: float = Field(default=0.0, ge=0)
    relative_humidity_percent: float = Field(default=50.0, ge=0, le=100)
    wind_speed_m_s: float = Field(default=2.0, ge=0)
