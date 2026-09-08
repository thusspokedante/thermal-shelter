from fastapi import APIRouter
from app.schemas.climate import ClimatePoint

router = APIRouter(tags=["climate"])

@router.post("/climate/validate")
def validate_climate(data: list[ClimatePoint]):
    return {"valid": True, "points": len(data)}
