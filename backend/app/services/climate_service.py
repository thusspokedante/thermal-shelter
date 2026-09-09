"""
Fetches historical hourly climate data from the Open-Meteo archive API and
normalizes it into the shape our thermal simulation flow expects.

Flow: request -> Open-Meteo -> normalize -> response
(No caching/storage here yet; that can be added later if needed.)
"""

from datetime import date

import httpx

from app.schemas.climate import ClimateHourlyPoint, ClimateLocation, ClimatePoint, ClimateResponse

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Variables we ask Open-Meteo for, and what the thermal model actually needs.
HOURLY_VARIABLES = (
    "temperature_2m,relative_humidity_2m,wind_speed_10m,"
    "wind_direction_10m,shortwave_radiation"
)

REQUEST_TIMEOUT_SECONDS = 15.0


def _validate_inputs(latitude: float, longitude: float, start_date: date, end_date: date) -> None:
    if not (-90 <= latitude <= 90):
        raise ValueError("latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise ValueError("longitude must be between -180 and 180")
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")


def _normalize(payload: dict, latitude: float, longitude: float) -> ClimateResponse:
    hourly = payload.get("hourly")
    if not hourly:
        raise ValueError("Open-Meteo response is missing 'hourly' data")

    try:
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        humidity = hourly["relative_humidity_2m"]
        wind_speed = hourly["wind_speed_10m"]
        wind_direction = hourly["wind_direction_10m"]
        solar = hourly["shortwave_radiation"]
    except KeyError as exc:
        raise ValueError(f"Open-Meteo response is missing expected field: {exc}")

    lengths = {len(times), len(temps), len(humidity), len(wind_speed), len(wind_direction), len(solar)}
    if len(lengths) != 1:
        raise ValueError("Open-Meteo hourly arrays have mismatched lengths")

    points = [
        ClimateHourlyPoint(
            time=times[i],
            temperature=temps[i],
            relative_humidity=humidity[i],
            wind_speed=wind_speed[i],
            wind_direction=wind_direction[i],
            solar_irradiance=solar[i],
        )
        for i in range(len(times))
    ]

    return ClimateResponse(
        location=ClimateLocation(latitude=latitude, longitude=longitude),
        hourly=points,
    )


def get_climate(latitude: float, longitude: float, start_date: date, end_date: date) -> ClimateResponse:
    _validate_inputs(latitude, longitude, start_date, end_date)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": HOURLY_VARIABLES,
        "wind_speed_unit": "ms",
        "timezone": "UTC",
    }

    try:
        response = httpx.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        raise TimeoutError("Timed out while contacting Open-Meteo")
    except httpx.ConnectError:
        raise ConnectionError("Could not connect to Open-Meteo")
    except httpx.RequestError as exc:
        raise ConnectionError(f"Error contacting Open-Meteo: {exc}")

    if response.status_code != 200:
        detail = response.text
        raise LookupError(f"Open-Meteo returned an error (status {response.status_code}): {detail}")

    try:
        payload = response.json()
    except ValueError:
        raise ValueError("Open-Meteo returned a malformed (non-JSON) response")

    return _normalize(payload, latitude, longitude)


def to_climate_points(hourly: list[ClimateHourlyPoint]) -> list[ClimatePoint]:
    """
    Convert normalized Open-Meteo hourly points (ClimateHourlyPoint) into the
    ClimatePoint structure expected by the thermal solver's SimulationRequest.

    This is a pure field-mapping/unit-alignment step - no resampling here.
    The thermal solver already interpolates the given climate series onto
    its own simulation timestep, so we pass the hourly series through as-is.
    """
    return [
        ClimatePoint(
            timestamp=point.time,
            outdoor_temperature_c=point.temperature,
            solar_irradiance_w_m2=point.solar_irradiance,
            relative_humidity_percent=point.relative_humidity,
            wind_speed_m_s=point.wind_speed,
        )
        for point in hourly
    ]
