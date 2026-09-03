from src.db.models.comentario_model import Comentario
from src.dtos.comentario_dto import (
    AutorComentarioDTO,
    ComentarioResponseDTO,
    CrearComentarioDTO,
    GuardarComentarioDTO,
)
from src.schemas.comentario_schema import CrearComentarioSchema, GetComentarioSchema


class ComentarioMapper:
    @staticmethod
    def to_create_dto(schema: CrearComentarioSchema) -> CrearComentarioDTO:
        return CrearComentarioDTO(**schema.model_dump())

    @staticmethod
    def to_model(data: GuardarComentarioDTO) -> Comentario:
        return Comentario(**data.model_dump())

    @staticmethod
    def to_response_dto(
        model: Comentario,
        *,
        cantidad_respuestas: int = 0,
    ) -> ComentarioResponseDTO:
        return ComentarioResponseDTO(
            id=model.id,
            publicacion_id=model.publicacion_id,
            usuario_id=model.usuario_id,
            contenido=model.contenido,
            fecha=model.fecha,
            comentario_padre_id=model.comentario_padre_id,
            autor=AutorComentarioDTO(
                id=model.autor.id,
                nombre=model.autor.nombre,
                headline=model.autor.headline,
                foto_perfil_url=model.autor.foto_perfil_url,
            ),
            cantidad_respuestas=cantidad_respuestas,
        )

    @staticmethod
    def to_response_schema(dto: ComentarioResponseDTO) -> GetComentarioSchema:
        return GetComentarioSchema.model_validate(dto)
