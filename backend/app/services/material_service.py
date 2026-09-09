from app.db import SessionLocal
from app.models.materials import Material


def _validate(data: dict):
    if data["thermal_conductivity_w_mk"] <= 0:
        raise ValueError("thermal_conductivity_w_mk must be > 0")
    if data["density_kg_m3"] <= 0:
        raise ValueError("density_kg_m3 must be > 0")
    if data["specific_heat_j_kgk"] <= 0:
        raise ValueError("specific_heat_j_kgk must be > 0")
    if not (0 <= data["solar_absorptance"] <= 1):
        raise ValueError("solar_absorptance must be between 0 and 1")


def list_materials():
    db = SessionLocal()
    try:
        materials = db.query(Material).order_by(Material.id).all()
        return [m.to_dict() for m in materials]
    finally:
        db.close()


def get_material(material_id: str):
    db = SessionLocal()
    try:
        m = db.get(Material, material_id)
        if m is None:
            raise ValueError(f"Unknown material: {material_id}")
        return m.to_dict()
    finally:
        db.close()


def add_material(data: dict):
    """Insert or update a material. Used by the optional add/update path."""
    _validate(data)
    db = SessionLocal()
    try:
        existing = db.get(Material, data["id"])
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            db.add(Material(**data))
        db.commit()
        return get_material(data["id"])
    finally:
        db.close()
