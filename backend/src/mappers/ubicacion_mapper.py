from src.dtos.ubicacion_dto import CiudadDTO
from src.schemas.ubicacion_schema import CiudadSchema


class UbicacionMapper:
    @staticmethod
    def to_schema(dto: CiudadDTO) -> CiudadSchema:
        return CiudadSchema(**dto.model_dump())
