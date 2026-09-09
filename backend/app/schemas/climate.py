from pydantic import BaseModel, Field

class ClimatePoint(BaseModel):
    timestamp: str
    outdoor_temperature_c: float
    solar_irradiance_w_m2: float = Field(default=0.0, ge=0)
    relative_humidity_percent: float = Field(default=50.0, ge=0, le=100)
    wind_speed_m_s: float = Field(default=2.0, ge=0)


class ClimateLocation(BaseModel):
    """Location echoed back with the normalized climate response."""
    latitude: float
    longitude: float


class ClimateHourlyPoint(BaseModel):
    """
    One hour of normalized climate data from the Open-Meteo historical
    (archive) API. Units:
      - temperature: degrees C
      - relative_humidity: percent (0-100)
      - wind_speed: meters/second
      - wind_direction: degrees (0-360, meteorological convention)
      - solar_irradiance: W/m^2 (shortwave / global horizontal irradiance)
    """
    time: str
    temperature: float
    relative_humidity: float = Field(ge=0, le=100)
    wind_speed: float = Field(ge=0)
    wind_direction: float = Field(ge=0, le=360)
    solar_irradiance: float = Field(ge=0)


class ClimateResponse(BaseModel):
    """Normalized response returned by GET /api/climate."""
    location: ClimateLocation
    hourly: list[ClimateHourlyPoint]
