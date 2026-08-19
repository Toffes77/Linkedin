from src.db.models.oferta_model import Oferta
from src.dtos.oferta_dto import (
    CreateOfertaDTO,
    OfertaEstadisticasDTO,
    OfertaResponseDTO,
    UpdateOfertaDTO,
)
from src.schemas.oferta_schema import (
    CreateOfertaSchema,
    GetOfertaEstadisticasSchema,
    GetOfertaSchema,
    UpdateOfertaSchema,
)


class OfertaMapper:
    @staticmethod
    def to_create_dto(schema: CreateOfertaSchema) -> CreateOfertaDTO:
        return CreateOfertaDTO(**schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdateOfertaSchema) -> UpdateOfertaDTO:
        return UpdateOfertaDTO(**schema.model_dump(exclude_unset=True))

    @staticmethod
    def to_model(data: CreateOfertaDTO) -> Oferta:
        return Oferta(**data.model_dump())

    @staticmethod
    def apply_update(model: Oferta, data: UpdateOfertaDTO) -> Oferta:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(oferta: Oferta) -> OfertaResponseDTO:
        return OfertaResponseDTO.model_validate(oferta)

    @staticmethod
    def to_response_schema(dto: OfertaResponseDTO) -> GetOfertaSchema:
        return GetOfertaSchema.model_validate(dto)

    @staticmethod
    def to_statistics_schema(dto: OfertaEstadisticasDTO) -> GetOfertaEstadisticasSchema:
        return GetOfertaEstadisticasSchema.model_validate(dto)
