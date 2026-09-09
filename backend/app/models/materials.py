from sqlalchemy import Column, String, Float
from app.db import Base


class Material(Base):
    """A building material and the properties the thermal solver needs."""

    __tablename__ = "materials"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    thermal_conductivity_w_mk = Column(Float, nullable=False)
    density_kg_m3 = Column(Float, nullable=False)
    specific_heat_j_kgk = Column(Float, nullable=False)
    solar_absorptance = Column(Float, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "thermal_conductivity_w_mk": self.thermal_conductivity_w_mk,
            "density_kg_m3": self.density_kg_m3,
            "specific_heat_j_kgk": self.specific_heat_j_kgk,
            "solar_absorptance": self.solar_absorptance,
        }
