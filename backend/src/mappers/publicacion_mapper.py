from src.db.models.publicacion_model import Publicacion
from src.dtos.publicacion_dto import (
    AutorPublicacionDTO,
    CreatePublicacionDTO,
    PublicacionCardDTO,
    PublicacionResponseDTO,
    UpdatePublicacionDTO,
)
from src.schemas.publicación_schemas import (
    CreatePublicacionSchema,
    GetPublicacionCardSchema,
    GetPublicacionSchema,
    UpdatePublicacionSchema,
)


class PublicacionMapper:
    @staticmethod
    def to_create_dto(
        schema: CreatePublicacionSchema,
        autor_id: int,
    ) -> CreatePublicacionDTO:
        return CreatePublicacionDTO(autor_id=autor_id, **schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdatePublicacionSchema) -> UpdatePublicacionDTO:
        return UpdatePublicacionDTO(**schema.model_dump(exclude_unset=True))

    @staticmethod
    def to_model(data: CreatePublicacionDTO) -> Publicacion:
        return Publicacion(**data.model_dump())

    @staticmethod
    def apply_update(model: Publicacion, data: UpdatePublicacionDTO) -> Publicacion:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(model: Publicacion) -> PublicacionResponseDTO:
        return PublicacionResponseDTO.model_validate(model)

    @staticmethod
    def to_card_dto(
        model: Publicacion,
        *,
        reacciones: dict[str, int],
        mi_reaccion: str | None,
        cantidad_comentarios: int,
    ) -> PublicacionCardDTO:
        return PublicacionCardDTO(
            **PublicacionMapper.to_response_dto(model).model_dump(),
            autor=AutorPublicacionDTO.model_validate(model.autor),
            reacciones=reacciones,
            mi_reaccion=mi_reaccion,
            cantidad_comentarios=cantidad_comentarios,
        )

    @staticmethod
    def to_response_schema(dto: PublicacionResponseDTO) -> GetPublicacionSchema:
        return GetPublicacionSchema.model_validate(dto)

    @staticmethod
    def to_card_schema(dto: PublicacionCardDTO) -> GetPublicacionCardSchema:
        return GetPublicacionCardSchema.model_validate(dto)
