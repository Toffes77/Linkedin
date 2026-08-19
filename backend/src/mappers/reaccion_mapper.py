from src.db.models.reaciones_model import Reacciones
from src.dtos.reacciones_dto import (
    CreateReaccionDTO,
    ReaccionResponseDTO,
    UpdateReaccionDTO,
)
from src.schemas.reaciones_schema import (
    CreateReaccionSchema,
    GetReaccionSchema,
    UpdateReaccionSchema,
)


class ReaccionMapper:
    @staticmethod
    def to_create_dto(
        schema: CreateReaccionSchema,
        usuario_id: int,
    ) -> CreateReaccionDTO:
        return CreateReaccionDTO(
            usuario_id=usuario_id,
            publicacion_id=schema.publicacion_id,
            tipo=schema.tipo,
        )

    @staticmethod
    def to_update_dto(schema: UpdateReaccionSchema) -> UpdateReaccionDTO:
        return UpdateReaccionDTO(**schema.model_dump())

    @staticmethod
    def to_model(data: CreateReaccionDTO) -> Reacciones:
        return Reacciones(**data.model_dump())

    @staticmethod
    def apply_update(model: Reacciones, data: UpdateReaccionDTO) -> Reacciones:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(model: Reacciones) -> ReaccionResponseDTO:
        return ReaccionResponseDTO.model_validate(model)

    @staticmethod
    def to_response_schema(dto: ReaccionResponseDTO) -> GetReaccionSchema:
        return GetReaccionSchema.model_validate(dto)
