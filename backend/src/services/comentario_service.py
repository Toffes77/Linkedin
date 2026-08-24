from sqlalchemy.orm import Session

from src.dtos.comentario_dto import (
    CantidadComentariosDTO,
    ComentarioResponseDTO,
    CrearComentarioDTO,
    GuardarComentarioDTO,
)
from src.mappers.comentario_mapper import ComentarioMapper
from src.repositories.comentario_repository import ComentarioRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.utils.errors import BadRequestError, ForbiddenError, NotFoundError


class ComentarioService:
    def __init__(self, db: Session):
        self.repository = ComentarioRepository(db)
        self.publicacion_repository = PublicacionRepository(db)

    def create(
        self,
        publicacion_id: int,
        data: CrearComentarioDTO,
        usuario_id: int,
    ) -> ComentarioResponseDTO:
        self._require_publicacion(publicacion_id)
        contenido = self._normalizar_contenido(data.contenido)
        comentario = self.repository.create(
            GuardarComentarioDTO(
                publicacion_id=publicacion_id,
                usuario_id=usuario_id,
                contenido=contenido,
            )
        )
        return ComentarioMapper.to_response_dto(comentario)

    def reply(
        self,
        comentario_id: int,
        data: CrearComentarioDTO,
        usuario_id: int,
    ) -> ComentarioResponseDTO:
        comentario_padre = self.repository.get_by_id(comentario_id)
        if comentario_padre is None:
            raise NotFoundError("Comentario no encontrado.")

        self._require_publicacion(comentario_padre.publicacion_id)
        contenido = self._normalizar_contenido(data.contenido)
        respuesta = self.repository.create(
            GuardarComentarioDTO(
                publicacion_id=comentario_padre.publicacion_id,
                usuario_id=usuario_id,
                contenido=contenido,
                comentario_padre_id=comentario_padre.id,
            )
        )
        return ComentarioMapper.to_response_dto(respuesta)

    def list_by_publicacion(
        self,
        publicacion_id: int,
    ) -> list[ComentarioResponseDTO]:
        self._require_publicacion(publicacion_id)
        return ComentarioMapper.to_response_tree(
            self.repository.get_all_by_publicacion(publicacion_id)
        )

    def count_by_publicacion(self, publicacion_id: int) -> CantidadComentariosDTO:
        self._require_publicacion(publicacion_id)
        return CantidadComentariosDTO(
            cantidad=self.repository.count_by_publicacion(publicacion_id)
        )

    def delete(self, comentario_id: int, usuario_id: int) -> None:
        comentario = self.repository.get_by_id(comentario_id)
        if comentario is None:
            raise NotFoundError("Comentario no encontrado.")
        if comentario.usuario_id != usuario_id:
            raise ForbiddenError("Solo el autor puede eliminar el comentario.")
        self.repository.delete(comentario)

    def _require_publicacion(self, publicacion_id: int) -> None:
        if self.publicacion_repository.get_by_id(publicacion_id) is None:
            raise NotFoundError("Publicación no encontrada.")

    @staticmethod
    def _normalizar_contenido(contenido: str) -> str:
        contenido_limpio = contenido.strip()
        if not contenido_limpio:
            raise BadRequestError("El comentario no puede estar vacío.")
        if len(contenido_limpio) > 1000:
            raise BadRequestError(
                "El comentario no puede superar los 1000 caracteres."
            )
        return contenido_limpio
