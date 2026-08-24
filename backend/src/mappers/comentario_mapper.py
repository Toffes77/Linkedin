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
        responses: list[ComentarioResponseDTO] | None = None,
    ) -> ComentarioResponseDTO:
        respuestas = responses or []
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
            cantidad_respuestas=len(respuestas),
            respuestas=respuestas,
        )

    @staticmethod
    def to_response_tree(
        models: list[Comentario],
    ) -> list[ComentarioResponseDTO]:
        children_by_parent: dict[int, list[Comentario]] = {}
        roots: list[Comentario] = []
        model_ids = {model.id for model in models}

        for model in models:
            if (
                model.comentario_padre_id is None
                or model.comentario_padre_id not in model_ids
            ):
                roots.append(model)
            else:
                children_by_parent.setdefault(
                    model.comentario_padre_id,
                    [],
                ).append(model)

        for children in children_by_parent.values():
            children.sort(key=lambda model: (model.fecha, model.id))

        def build_node(model: Comentario) -> ComentarioResponseDTO:
            responses = [
                build_node(child)
                for child in children_by_parent.get(model.id, [])
            ]
            return ComentarioMapper.to_response_dto(
                model,
                responses=responses,
            )

        roots.sort(key=lambda model: (model.fecha, model.id), reverse=True)
        return [build_node(root) for root in roots]

    @staticmethod
    def to_response_schema(dto: ComentarioResponseDTO) -> GetComentarioSchema:
        return GetComentarioSchema.model_validate(dto)
