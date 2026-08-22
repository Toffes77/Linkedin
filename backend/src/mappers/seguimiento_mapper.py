from src.db.models.seguimiento_model import Seguimiento
from src.dtos.seguimiento_dto import (
    EstadoSeguimientoResponseDTO,
    SeguimientoResponseDTO,
)
from src.schemas.seguimiento_schema import (
    EstadoSeguimientoResponseSchema,
    SeguimientoResponseSchema,
)


class SeguimientoMapper:
    @staticmethod
    def to_response_dto(model: Seguimiento) -> SeguimientoResponseDTO:
        return SeguimientoResponseDTO.model_validate(model)

    @staticmethod
    def to_response_schema(dto: SeguimientoResponseDTO) -> SeguimientoResponseSchema:
        return SeguimientoResponseSchema.model_validate(dto)

    @staticmethod
    def to_status_schema(
        dto: EstadoSeguimientoResponseDTO,
    ) -> EstadoSeguimientoResponseSchema:
        return EstadoSeguimientoResponseSchema.model_validate(dto)
