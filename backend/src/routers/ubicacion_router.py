from fastapi import APIRouter, Query

from src.mappers.ubicacion_mapper import UbicacionMapper
from src.schemas.ubicacion_schema import CiudadSchema
from src.services.ubicacion_service import UbicacionService


router = APIRouter(prefix="/ubicaciones", tags=["ubicaciones"])


@router.get("/ciudades", response_model=list[CiudadSchema])
def search_cities(
    q: str = Query(min_length=2, max_length=100, pattern=r".*\S.*"),
    limit: int = Query(default=10, ge=1, le=15),
):
    cities = UbicacionService().search_cities(q, limit)
    return [UbicacionMapper.to_schema(city) for city in cities]
