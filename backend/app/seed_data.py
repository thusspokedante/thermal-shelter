# Prototype engineering values for the initial material catalog.
# Replace with verified/sourced values before using results for real
# construction decisions.

SEED_MATERIALS = [
    {"id": "stone", "name": "Stone", "thermal_conductivity_w_mk": 2.00, "density_kg_m3": 2400, "specific_heat_j_kgk": 800, "solar_absorptance": 0.70},
    {"id": "concrete", "name": "Concrete", "thermal_conductivity_w_mk": 1.70, "density_kg_m3": 2300, "specific_heat_j_kgk": 880, "solar_absorptance": 0.65},
    {"id": "brick", "name": "Brick", "thermal_conductivity_w_mk": 0.70, "density_kg_m3": 1800, "specific_heat_j_kgk": 840, "solar_absorptance": 0.60},
    {"id": "aac", "name": "AAC", "thermal_conductivity_w_mk": 0.128, "density_kg_m3": 477, "specific_heat_j_kgk": 900, "solar_absorptance": 0.60},
    {"id": "rammed_earth", "name": "Rammed Earth", "thermal_conductivity_w_mk": 0.55, "density_kg_m3": 2000, "specific_heat_j_kgk": 760, "solar_absorptance": 0.60},
    {"id": "wood", "name": "Timber", "thermal_conductivity_w_mk": 0.15, "density_kg_m3": 600, "specific_heat_j_kgk": 1600, "solar_absorptance": 0.70},
    {"id": "plywood", "name": "Plywood", "thermal_conductivity_w_mk": 0.113, "density_kg_m3": 550, "specific_heat_j_kgk": 1380, "solar_absorptance": 0.60},
    {"id": "mineral_wool", "name": "Mineral Wool", "thermal_conductivity_w_mk": 0.040, "density_kg_m3": 100, "specific_heat_j_kgk": 840, "solar_absorptance": 0.40},
    {"id": "glass_wool", "name": "Glass Wool", "thermal_conductivity_w_mk": 0.040, "density_kg_m3": 120, "specific_heat_j_kgk": 750, "solar_absorptance": 0.40},
    {"id": "eps_insulation", "name": "EPS Insulation", "thermal_conductivity_w_mk": 0.035, "density_kg_m3": 30, "specific_heat_j_kgk": 1400, "solar_absorptance": 0.40},
    {"id": "xps_insulation", "name": "XPS Insulation", "thermal_conductivity_w_mk": 0.030, "density_kg_m3": 35, "specific_heat_j_kgk": 1450, "solar_absorptance": 0.40},
    {"id": "polyurethane", "name": "Polyurethane", "thermal_conductivity_w_mk": 0.025, "density_kg_m3": 35, "specific_heat_j_kgk": 1800, "solar_absorptance": 0.40},
    {"id": "plaster", "name": "Plaster", "thermal_conductivity_w_mk": 0.50, "density_kg_m3": 1000, "specific_heat_j_kgk": 1090, "solar_absorptance": 0.50},
    {"id": "glass", "name": "Glass", "thermal_conductivity_w_mk": 1.00, "density_kg_m3": 2500, "specific_heat_j_kgk": 750, "solar_absorptance": 0.10},
]


def seed(session):
    """Insert all seed materials. Safe to call repeatedly (skips existing IDs)."""
    from app.models.materials import Material

    inserted = 0
    for data in SEED_MATERIALS:
        if session.get(Material, data["id"]) is not None:
            continue
        session.add(Material(**data))
        inserted += 1
    session.commit()
    return inserted
