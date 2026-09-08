from fastapi import APIRouter, HTTPException
from app.services.material_service import list_materials, get_material

router = APIRouter(tags=["materials"])


@router.get("/materials")
def get_materials():
    return {"materials": list_materials()}


@router.get("/materials/{material_id}")
def get_material_by_id(material_id: str):
    try:
        return get_material(material_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
