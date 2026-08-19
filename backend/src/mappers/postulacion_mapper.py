from src.db.models.postulacion_model import Postulacion
from src.dtos.postulacion_dto import (
    CreatePostulacionDTO,
    PostulacionResponseDTO,
    UpdatePostulacionDTO,
)
from src.schemas.postulacion_schema import (
    CreatePostulacionSchema,
    GetPostulacionSchema,
    UpdatePostulacionSchema,
)


class PostulacionMapper:
    @staticmethod
    def to_create_dto(
        schema: CreatePostulacionSchema,
        usuario_id: int,
    ) -> CreatePostulacionDTO:
        return CreatePostulacionDTO(oferta_id=schema.oferta_id, usuario_id=usuario_id)

    @staticmethod
    def to_update_dto(schema: UpdatePostulacionSchema) -> UpdatePostulacionDTO:
        return UpdatePostulacionDTO(**schema.model_dump())

    @staticmethod
    def to_model(data: CreatePostulacionDTO) -> Postulacion:
        return Postulacion(**data.model_dump())

    @staticmethod
    def apply_update(model: Postulacion, data: UpdatePostulacionDTO) -> Postulacion:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(postulacion: Postulacion) -> PostulacionResponseDTO:
        return PostulacionResponseDTO.model_validate(postulacion)

    @staticmethod
    def to_response_schema(dto: PostulacionResponseDTO) -> GetPostulacionSchema:
        return GetPostulacionSchema.model_validate(dto)
