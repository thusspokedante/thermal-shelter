import math
from app.services.material_service import get_material

SIGMA = 5.670374419e-8
RHO_AIR = 1.225
CP_AIR = 1005.0

def layer_u_value(layers):
    resistance = 0.0
    for layer in layers:
        m = get_material(layer.material_id)
        resistance += layer.thickness_m / m["thermal_conductivity_w_mk"]
    # Approximate inside/outside surface resistances.
    resistance += 0.12 + 0.04
    return 1.0 / resistance

def construction_heat_capacity(layers, area):
    total = 0.0
    for layer in layers:
        m = get_material(layer.material_id)
        total += m["density_kg_m3"] * layer.thickness_m * area * m["specific_heat_j_kgk"]
    return total

def solar_absorptance(layers):
    # Area-weighted simplification using the first/main layer.
    m = get_material(layers[0].material_id)
    return m["solar_absorptance"]

def simulate(req):
    g = req.geometry
    s = req.settings

    floor_area = g.length_m * g.width_m
    roof_area = floor_area
    wall_area_gross = 2 * (g.length_m + g.width_m) * g.height_m

    window_area = sum(x.area_m2 for x in req.windows)
    door_area = sum(x.area_m2 for x in req.doors)
    wall_opaque_area = max(0.0, wall_area_gross - window_area - door_area)

    wall_u = layer_u_value(req.wall.layers)
    roof_u = layer_u_value(req.roof.layers)
    floor_u = layer_u_value(req.floor.layers)

    # Lumped effective thermal capacitance.
    wall_cap = construction_heat_capacity(req.wall.layers, wall_opaque_area)
    roof_cap = construction_heat_capacity(req.roof.layers, roof_area)
    floor_cap = construction_heat_capacity(req.floor.layers, floor_area)

    volume = floor_area * g.height_m
    air_cap = RHO_AIR * volume * CP_AIR

    # Use a fraction of envelope mass as dynamically effective in this
    # reduced-order model; a full multilayer finite-difference wall model
    # can replace this later.
    effective_cap = air_cap + 0.20 * (wall_cap + roof_cap + floor_cap)
    effective_cap = max(effective_cap, 1.0)

    dt = s.timestep_minutes * 60.0
    expected_points = int(round(s.duration_hours * 60 / s.timestep_minutes)) + 1

    # Interpolate climate to the requested simulation time grid.
    climate = sorted(req.climate, key=lambda x: x.timestamp)
    temps = [x.outdoor_temperature_c for x in climate]
    solar = [x.solar_irradiance_w_m2 for x in climate]
    wind = [x.wind_speed_m_s for x in climate]

    def interp(values, i):
        if len(values) == expected_points:
            return values[i]
        position = i * (len(values) - 1) / max(expected_points - 1, 1)
        lo = int(math.floor(position))
        hi = min(lo + 1, len(values) - 1)
        f = position - lo
        return values[lo] * (1-f) + values[hi] * f

    indoor = s.initial_indoor_temperature_c

    total_solar_j = 0.0
    total_losses_j = {
        "wall": 0.0, "roof": 0.0, "floor": 0.0,
        "windows": 0.0, "doors": 0.0,
        "infiltration": 0.0, "radiation": 0.0
    }

    rows = []

    for i in range(expected_points):
        outdoor = interp(temps, i)
        ghi = max(0.0, interp(solar, i))
        wind_speed = max(0.0, interp(wind, i))

        # Simple outdoor convection coefficient.
        h_out = 5.8 + 4.1 * wind_speed
        h_in = 2.5

        wall_q = wall_u * wall_opaque_area * (outdoor - indoor)
        roof_q = roof_u * roof_area * (outdoor - indoor)
        floor_q = floor_u * floor_area * (outdoor - indoor)

        window_q = sum(o.u_value_w_m2k * o.area_m2 * (outdoor - indoor)
                       for o in req.windows)
        door_q = sum(o.u_value_w_m2k * o.area_m2 * (outdoor - indoor)
                     for o in req.doors)

        # Infiltration sensible heat exchange.
        volumetric_flow_m3_s = s.air_changes_per_hour * volume / 3600.0
        infiltration_q = RHO_AIR * CP_AIR * volumetric_flow_m3_s * (outdoor - indoor)

        # Long-wave radiation to an approximate sky temperature.
        sky_k = (outdoor + 273.15) - 6.0
        surface_k = indoor + 273.15
        emissivity = 0.90
        exposed_area = wall_opaque_area + roof_area
        radiation_loss = emissivity * SIGMA * exposed_area * (surface_k**4 - sky_k**4)
        radiation_q = -radiation_loss

        # Solar gain through glazing.
        solar_window_q = sum(
            ghi * o.area_m2 * o.shgc * o.solar_exposure_factor
            for o in req.windows
        )

        # Simplified absorbed solar gain by roof + opaque walls.
        solar_surface_q = ghi * (
            roof_area * solar_absorptance(req.roof.layers) * 0.15 +
            wall_opaque_area * solar_absorptance(req.wall.layers) * 0.05
        )

        solar_gain = solar_window_q + solar_surface_q
        internal_gain = s.indoor_heat_gain_w

        # Positive Q warms indoor space; negative Q removes heat.
        q_envelope = wall_q + roof_q + floor_q + window_q + door_q
        q_infiltration = infiltration_q

        q_net = (
            q_envelope +
            q_infiltration +
            radiation_q +
            solar_gain +
            internal_gain
        )

        if i < expected_points - 1:
            indoor = indoor + (q_net / effective_cap) * dt

        hours = i * s.timestep_minutes / 60.0

        # Store loss magnitude when heat is flowing from inside to outside.
        def loss_j(q):
            return max(0.0, -q) * dt

        total_losses_j["wall"] += loss_j(wall_q)
        total_losses_j["roof"] += loss_j(roof_q)
        total_losses_j["floor"] += loss_j(floor_q)
        total_losses_j["windows"] += loss_j(window_q)
        total_losses_j["doors"] += loss_j(door_q)
        total_losses_j["infiltration"] += loss_j(infiltration_q)
        total_losses_j["radiation"] += loss_j(radiation_q)
        total_solar_j += max(0.0, solar_gain) * dt

        rows.append({
            "time_hours": round(hours, 4),
            "outdoor_temperature_c": round(outdoor, 4),
            "indoor_temperature_c": round(indoor, 4),
            "solar_irradiance_w_m2": round(ghi, 4),
            "solar_gain_w": round(solar_gain, 4),
            "wall_heat_flow_w": round(wall_q, 4),
            "roof_heat_flow_w": round(roof_q, 4),
            "floor_heat_flow_w": round(floor_q, 4),
            "window_heat_flow_w": round(window_q, 4),
            "door_heat_flow_w": round(door_q, 4),
            "infiltration_heat_flow_w": round(infiltration_q, 4),
            "radiation_heat_flow_w": round(radiation_q, 4),
            "internal_gain_w": round(internal_gain, 4),
            "net_heat_flow_w": round(q_net, 4),
        })

    indoor_values = [r["indoor_temperature_c"] for r in rows]
    comfort_hours = sum(
        s.comfort_min_c <= x <= s.comfort_max_c
        for x in indoor_values
    ) * s.timestep_minutes / 60.0

    loss_kwh = {k: v / 3_600_000 for k, v in total_losses_j.items()}

    return {
        "summary": {
            "simulation_duration_hours": s.duration_hours,
            "timestep_minutes": s.timestep_minutes,
            "indoor_temperature_min_c": round(min(indoor_values), 3),
            "indoor_temperature_max_c": round(max(indoor_values), 3),
            "indoor_temperature_average_c": round(sum(indoor_values) / len(indoor_values), 3),
            "comfort_hours": round(comfort_hours, 3),
            "solar_energy_captured_kwh": round(total_solar_j / 3_600_000, 3),
            "total_heat_loss_kwh": round(sum(loss_kwh.values()), 3),
            "wall_u_value_w_m2k": round(wall_u, 4),
            "roof_u_value_w_m2k": round(roof_u, 4),
            "floor_u_value_w_m2k": round(floor_u, 4),
            "effective_thermal_capacity_j_k": round(effective_cap, 1),
        },
        "time_series": rows,
        "heat_loss_breakdown": {k: round(v, 4) for k, v in loss_kwh.items()},
        "assumptions": [
            "Reduced-order lumped transient thermal model.",
            "Constant material properties.",
            "Approximate inside/outside surface resistances.",
            "Outdoor convection coefficient depends on wind speed.",
            "Long-wave radiation uses an approximate sky temperature equal to outdoor temperature minus 6 C.",
            "Solar geometry, shading and detailed surface radiation are simplified.",
            "A fraction of envelope thermal mass is represented as dynamically effective.",
            "Comfort limits are configurable and are not a claim of ASHRAE compliance.",
        ],
    }
