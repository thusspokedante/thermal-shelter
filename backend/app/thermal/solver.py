import math
from app.services.material_service import get_material


SIGMA = 5.670374419e-8
RHO_AIR = 1.225
CP_AIR = 1005.0


def layer_u_value(layers):
    resistance = 0.0

    for layer in layers:
        m = get_material(layer.material_id)
        resistance += (
            layer.thickness_m
            / m["thermal_conductivity_w_mk"]
        )

    # Approximate inside/outside surface resistances.
    resistance += 0.12 + 0.04

    return 1.0 / resistance


def construction_heat_capacity(layers, area):
    total = 0.0

    for layer in layers:
        m = get_material(layer.material_id)

        total += (
            m["density_kg_m3"]
            * layer.thickness_m
            * area
            * m["specific_heat_j_kgk"]
        )

    return total


def solar_absorptance(layers):
    # Area-weighted simplification using the first/main layer.
    m = get_material(layers[0].material_id)
    return m["solar_absorptance"]


def sky_temperature(outdoor_temperature_c):
    """
    Simple effective sky-temperature approximation.

    The sky is assumed to be approximately 6 C colder
    than the outdoor air temperature.
    """
    return outdoor_temperature_c - 6.0


def estimate_ground_temperature_series(outdoor_temperatures, dt_seconds):
    """
    Estimate a ground-reference temperature from outdoor temperature using
    a simple first-order low-pass response.

    The ground is initialized to the mean outdoor temperature over the
    supplied simulation period and responds slowly with a 72-hour time
    constant. This is a reduced-order approximation, not a soil model.
    """
    if not outdoor_temperatures:
        return []

    time_constant_seconds = 72.0 * 3600.0
    alpha = 1.0 - math.exp(-dt_seconds / time_constant_seconds)

    ground = sum(outdoor_temperatures) / len(outdoor_temperatures)
    result = []

    for outdoor in outdoor_temperatures:
        result.append(ground)
        ground += alpha * (outdoor - ground)

    return result


def longwave_radiation(
    surface_temperature_c,
    surroundings_temperature_c,
    area,
    emissivity=0.90
):
    """
    Net longwave radiation from an exterior surface
    to the sky/surroundings.

    Positive value = heat loss from the surface.
    Negative value = heat gain by the surface.
    """

    surface_k = surface_temperature_c + 273.15
    surroundings_k = surroundings_temperature_c + 273.15

    return (
        emissivity
        * SIGMA
        * area
        * (surface_k ** 4 - surroundings_k ** 4)
    )


def simulate(req):
    g = req.geometry
    s = req.settings

    floor_area = g.length_m * g.width_m
    roof_area = floor_area

    wall_area_gross = (
        2
        * (g.length_m + g.width_m)
        * g.height_m
    )

    window_area = sum(
        x.area_m2 for x in req.windows
    )

    door_area = sum(
        x.area_m2 for x in req.doors
    )

    wall_opaque_area = max(
        0.0,
        wall_area_gross - window_area - door_area
    )

    wall_u = layer_u_value(req.wall.layers)
    roof_u = layer_u_value(req.roof.layers)
    floor_u = layer_u_value(req.floor.layers)

    wall_cap = construction_heat_capacity(
        req.wall.layers,
        wall_opaque_area
    )

    roof_cap = construction_heat_capacity(
        req.roof.layers,
        roof_area
    )

    floor_cap = construction_heat_capacity(
        req.floor.layers,
        floor_area
    )

    volume = floor_area * g.height_m

    air_cap = (
        RHO_AIR
        * volume
        * CP_AIR
    )

    effective_cap = (
        air_cap
        + 0.20
        * (
            wall_cap
            + roof_cap
            + floor_cap
        )
    )

    effective_cap = max(
        effective_cap,
        1.0
    )

    dt = s.timestep_minutes * 60.0

    expected_points = (
        int(
            round(
                s.duration_hours
                * 60
                / s.timestep_minutes
            )
        )
        + 1
    )

    climate = sorted(
        req.climate,
        key=lambda x: x.timestamp
    )

    temps = [
        x.outdoor_temperature_c
        for x in climate
    ]

    solar = [
        x.solar_irradiance_w_m2
        for x in climate
    ]

    wind = [
        x.wind_speed_m_s
        for x in climate
    ]

    def interp(values, i):
        if len(values) == expected_points:
            return values[i]

        position = (
            i
            * (len(values) - 1)
            / max(expected_points - 1, 1)
        )

        lo = int(math.floor(position))

        hi = min(
            lo + 1,
            len(values) - 1
        )

        f = position - lo

        return (
            values[lo] * (1 - f)
            + values[hi] * f
        )

    ground_temperatures = estimate_ground_temperature_series(
        temps,
        dt
    )

    indoor = s.initial_indoor_temperature_c

    total_solar_j = 0.0

    total_losses_j = {
        "wall": 0.0,
        "roof": 0.0,
        "floor": 0.0,
        "windows": 0.0,
        "doors": 0.0,
        "infiltration": 0.0,
        "radiation": 0.0
    }

    rows = []

    for i in range(expected_points):

        outdoor = interp(
            temps,
            i
        )

        ghi = max(
            0.0,
            interp(solar, i)
        )

        wind_speed = max(
            0.0,
            interp(wind, i)
        )

        # Outside convection coefficient.
        h_out = 5.8 + 4.1 * wind_speed

        # ---------------------------------------------------------
        # CONDUCTION
        # ---------------------------------------------------------

        wall_q = (
            wall_u
            * wall_opaque_area
            * (outdoor - indoor)
        )

        roof_q = (
            roof_u
            * roof_area
            * (outdoor - indoor)
        )

        ground_temperature = interp(
            ground_temperatures,
            i
        )

        floor_q = (
            floor_u
            * floor_area
            * (ground_temperature - indoor)
        )

        window_q = sum(
            o.u_value_w_m2k
            * o.area_m2
            * (outdoor - indoor)
            for o in req.windows
        )

        door_q = sum(
            o.u_value_w_m2k
            * o.area_m2
            * (outdoor - indoor)
            for o in req.doors
        )

        # ---------------------------------------------------------
        # INFILTRATION
        # ---------------------------------------------------------

        volumetric_flow_m3_s = (
            s.air_changes_per_hour
            * volume
            / 3600.0
        )

        infiltration_q = (
            RHO_AIR
            * CP_AIR
            * volumetric_flow_m3_s
            * (outdoor - indoor)
        )

        # ---------------------------------------------------------
        # EXTERIOR LONGWAVE RADIATION
        # ---------------------------------------------------------

        sky_c = sky_temperature(outdoor)

        emissivity = 0.90

        # Estimate exterior wall surface temperature.
        if wall_opaque_area > 0 and h_out > 0:
            wall_surface_c = (
                outdoor
                - wall_q
                / (h_out * wall_opaque_area)
            )
        else:
            wall_surface_c = outdoor

        # Estimate exterior roof surface temperature.
        if roof_area > 0 and h_out > 0:
            roof_surface_c = (
                outdoor
                - roof_q
                / (h_out * roof_area)
            )
        else:
            roof_surface_c = outdoor

        # Roof has a stronger view of the sky.
        roof_radiation_loss = longwave_radiation(
            roof_surface_c,
            sky_c,
            roof_area,
            emissivity
        )

        # Walls see a mixture of sky, ground and surroundings.
        # A simple reduced-order approximation is used:
        # only part of the wall area exchanges directly with
        # the effective sky temperature.
        wall_sky_area = (
            0.30 * wall_opaque_area
        )

        wall_radiation_loss = longwave_radiation(
            wall_surface_c,
            sky_c,
            wall_sky_area,
            emissivity
        )

        total_radiation_loss = (
            roof_radiation_loss
            + wall_radiation_loss
        )

        # Radiation is a heat LOSS from the shelter when positive.
        radiation_q = -total_radiation_loss

        # ---------------------------------------------------------
        # SOLAR GAINS
        # ---------------------------------------------------------

        solar_window_q = sum(
            ghi
            * o.area_m2
            * o.shgc
            * o.solar_exposure_factor
            for o in req.windows
        )

        solar_surface_q = ghi * (
            roof_area
            * solar_absorptance(req.roof.layers)
            * 0.15
            +
            wall_opaque_area
            * solar_absorptance(req.wall.layers)
            * 0.05
        )

        solar_gain = (
            solar_window_q
            + solar_surface_q
        )

        # ---------------------------------------------------------
        # INTERNAL GAINS
        # ---------------------------------------------------------

        internal_gain = s.indoor_heat_gain_w

        # ---------------------------------------------------------
        # NET HEAT FLOW
        # ---------------------------------------------------------

        q_envelope = (
            wall_q
            + roof_q
            + floor_q
            + window_q
            + door_q
        )

        q_infiltration = infiltration_q

        q_net = (
            q_envelope
            + q_infiltration
            + radiation_q
            + solar_gain
            + internal_gain
        )

        hours = (
            i
            * s.timestep_minutes
            / 60.0
        )

        # ---------------------------------------------------------
        # ENERGY ACCOUNTING
        # ---------------------------------------------------------

        # Row i represents the interval from row i to row i+1.
        # The final row has no following interval, so it must not
        # contribute to integrated energy totals.
        if i < expected_points - 1:
            def loss_j(q):
                return max(
                    0.0,
                    -q
                ) * dt

            total_losses_j["wall"] += loss_j(
                wall_q
            )

            total_losses_j["roof"] += loss_j(
                roof_q
            )

            total_losses_j["floor"] += loss_j(
                floor_q
            )

            total_losses_j["windows"] += loss_j(
                window_q
            )

            total_losses_j["doors"] += loss_j(
                door_q
            )

            total_losses_j["infiltration"] += loss_j(
                infiltration_q
            )

            total_losses_j["radiation"] += loss_j(
                radiation_q
            )

            total_solar_j += (
                max(0.0, solar_gain)
                * dt
            )

        # ---------------------------------------------------------
        # RESULT ROW
        # ---------------------------------------------------------

        rows.append({
            "time_hours": hours,
            "outdoor_temperature_c": outdoor,
            "indoor_temperature_c": indoor,
            "solar_irradiance_w_m2": ghi,
            "solar_gain_w": solar_gain,
            "wall_heat_flow_w": wall_q,
            "roof_heat_flow_w": roof_q,
            "floor_heat_flow_w": floor_q,
            "window_heat_flow_w": window_q,
            "door_heat_flow_w": door_q,
            "infiltration_heat_flow_w": infiltration_q,
            "radiation_heat_flow_w": radiation_q,
            "internal_heat_gain_w": internal_gain,
            "net_heat_flow_w": q_net
        })

        # Forward-Euler update: heat flow evaluated at row i advances
        # the indoor temperature to the next timestep. Keeping this
        # after rows.append ensures time_hours == 0 contains the exact
        # user-specified initial indoor temperature.
        if i < expected_points - 1:
            indoor = (
                indoor
                + (q_net / effective_cap) * dt
            )

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------

    indoor_values = [
        row["indoor_temperature_c"]
        for row in rows
    ]

    # Count comfort over simulated intervals, not sample points.
    comfort_hours = sum(
        1
        for row in rows[:-1]
        if (
            s.comfort_min_c
            <= row["indoor_temperature_c"]
            <= s.comfort_max_c
        )
    ) * (
        s.timestep_minutes / 60.0
    )

    total_heat_loss_kwh = (
        sum(total_losses_j.values())
        / 3_600_000.0
    )

    total_solar_kwh = (
        total_solar_j
        / 3_600_000.0
    )

    average_indoor = (
        sum(indoor_values)
        / len(indoor_values)
        if indoor_values
        else indoor
    )

    # -------------------------------------------------------------
    # RESPONSE
    # -------------------------------------------------------------

    return {
        "summary": {
            "duration_hours": s.duration_hours,
            "timestep_minutes": s.timestep_minutes,

            "indoor_temperature_min_c": min(
                indoor_values
            ),

            "indoor_temperature_max_c": max(
                indoor_values
            ),

            "indoor_temperature_average_c": average_indoor,

            "comfort_hours": comfort_hours,

            "solar_energy_captured_kwh": (
                total_solar_kwh
            ),

            "total_heat_loss_kwh": (
                total_heat_loss_kwh
            ),

            "wall_u_value_w_m2k": wall_u,
            "roof_u_value_w_m2k": roof_u,
            "floor_u_value_w_m2k": floor_u,

            "effective_thermal_capacity_j_k": (
                effective_cap
            )
        },

        "time_series": rows,

        "heat_loss_breakdown": {
            key: value / 3_600_000.0
            for key, value in total_losses_j.items()
        },

        "assumptions": [
            "Outdoor sky temperature is approximated as 6 C below outdoor air temperature.",
            "Exterior longwave radiation is calculated using estimated exterior surface temperatures.",
            "Roof radiation is assumed to have a stronger view of the sky than wall surfaces.",
            "30% of opaque wall area is assumed to exchange directly with the effective sky temperature.",
            "Thermal mass contribution is approximated as 20% of the construction heat capacity.",
            "Solar surface gains use simplified absorptance and exposure factors.",
            "The floor is modeled using the supplied floor construction U-value.",
            "Ground temperature is approximated using a 72-hour first-order response to outdoor temperature, initialized from the mean outdoor temperature of the supplied simulation period.",
            "Climate values are interpolated to match the requested simulation timestep."
        ]
    }