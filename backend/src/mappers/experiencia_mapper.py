from src.db.models.experiencia_model import Experiencia
from src.dtos.experiencia_dto import (
    CreateExperienciaDTO,
    ExperienciaResponseDTO,
    UpdateExperienciaDTO,
)
from src.schemas.experiencia_schema import (
    CreateExperienciaSchema,
    GetExperienciaSchema,
    UpdateExperienciaSchema,
)


class ExperienciaMapper:
    @staticmethod
    def to_create_dto(
        schema: CreateExperienciaSchema,
        usuario_id: int,
    ) -> CreateExperienciaDTO:
        return CreateExperienciaDTO(usuario_id=usuario_id, **schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdateExperienciaSchema) -> UpdateExperienciaDTO:
        return UpdateExperienciaDTO(**schema.model_dump(exclude_unset=True))

    @staticmethod
    def to_model(data: CreateExperienciaDTO) -> Experiencia:
        return Experiencia(**data.model_dump())

    @staticmethod
    def apply_update(model: Experiencia, data: UpdateExperienciaDTO) -> Experiencia:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(model: Experiencia) -> ExperienciaResponseDTO:
        return ExperienciaResponseDTO.model_validate(model)

    @staticmethod
    def to_response_schema(dto: ExperienciaResponseDTO) -> GetExperienciaSchema:
        return GetExperienciaSchema.model_validate(dto)
