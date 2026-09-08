from fastapi import APIRouter, Query

from src.mappers.ubicacion_mapper import UbicacionMapper
from src.schemas.ubicacion_schema import CiudadSchema
from src.services.ubicacion_service import UbicacionService
from src.utils.openapi import error_responses


router = APIRouter(prefix="/ubicaciones", tags=["ubicaciones"])


@router.get(
    "/ciudades",
    response_model=list[CiudadSchema],
    summary="Buscar ciudades",
    description=(
        "Busca ciudades del catálogo por texto parcial. Es el catálogo que se "
        "usa para validar y normalizar la ciudad de los perfiles."
    ),
)
def search_cities(
    q: str = Query(
        min_length=2,
        max_length=100,
        pattern=r".*\S.*",
        description="Texto parcial de al menos 2 caracteres.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=15,
        description="Cantidad máxima de coincidencias (1 a 15).",
    ),
):
    cities = UbicacionService().search_cities(q, limit)
    return [UbicacionMapper.to_schema(city) for city in cities]
