from src.dtos.ubicacion_dto import CiudadDTO
from src.utils.city_catalog import get_city_catalog
from src.utils.errors import BadRequestError


class UbicacionService:
    def search_cities(self, query: str, limit: int = 10) -> list[CiudadDTO]:
        term = query.strip()
        if len(term) < 2:
            return []
        return [
            CiudadDTO(pais=record.pais, ciudad=record.ciudad, nombre=record.nombre)
            for record in get_city_catalog().search(term, limit)
        ]

    def canonicalize_city(self, value: str) -> str:
        record = get_city_catalog().canonicalize(value.strip())
        if record is None:
            raise BadRequestError("Seleccioná una ciudad válida de la lista.")
        return record.nombre
