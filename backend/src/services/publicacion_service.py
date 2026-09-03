from sqlalchemy.orm import Session

from src.dtos.publicacion_dto import (
    CreatePublicacionDTO,
    PublicacionCardDTO,
    PublicacionResponseDTO,
    UpdatePublicacionDTO,
)
from src.mappers.publicacion_mapper import PublicacionMapper
from src.repositories.comentario_repository import ComentarioRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.reacciones_repository import ReaccionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ForbiddenError, NotFoundError


class PublicacionService:
    def __init__(self, db: Session):
        self.repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.comentario_repository = ComentarioRepository(db)
        self.reaccion_repository = ReaccionRepository(db)

    def create(
        self,
        publicacion_data: CreatePublicacionDTO,
    ) -> PublicacionResponseDTO:
        self._validar_usuario(publicacion_data.autor_id)

        publicacion = self.repository.create(publicacion_data)
        return PublicacionMapper.to_response_dto(publicacion)

    def get_by_id(
        self,
        publicacion_id: int,
        usuario_actual_id: int | None = None,
    ) -> PublicacionCardDTO:
        publicacion = self.repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada.")

        return self.to_card_dtos([publicacion], usuario_actual_id)[0]

    def get_by_autor(
        self,
        autor_id: int,
        limit: int | None = None,
        offset: int = 0,
        usuario_actual_id: int | None = None,
    ) -> list[PublicacionCardDTO]:
        self._validar_usuario(autor_id)
        publicaciones = self.repository.get_by_autor(autor_id, limit, offset)
        return self.to_card_dtos(publicaciones, usuario_actual_id)

    def to_card_dtos(
        self,
        publicaciones,
        usuario_actual_id: int | None,
    ) -> list[PublicacionCardDTO]:
        publicacion_ids = [publicacion.id for publicacion in publicaciones]
        conteos = {
            publicacion_id: {
                "like": 0,
                "celebrar": 0,
                "apoyar": 0,
                "interesante": 0,
            }
            for publicacion_id in publicacion_ids
        }
        reacciones_actuales: dict[int, str] = {}
        for publicacion_id, tipo, cantidad, es_reaccion_actual in (
            self.reaccion_repository.summarize_by_publicaciones(
                publicacion_ids,
                usuario_actual_id,
            )
        ):
            conteos[publicacion_id][tipo] = cantidad
            if es_reaccion_actual:
                reacciones_actuales[publicacion_id] = tipo
        comentarios = self.comentario_repository.count_by_publicaciones(
            publicacion_ids
        )
        return [
            PublicacionMapper.to_card_dto(
                publicacion,
                reacciones=conteos[publicacion.id],
                mi_reaccion=reacciones_actuales.get(publicacion.id),
                cantidad_comentarios=comentarios.get(publicacion.id, 0),
            )
            for publicacion in publicaciones
        ]

    def update(
        self,
        publicacion_id: int,
        usuario_id: int,
        publicacion_data: UpdatePublicacionDTO,
    ) -> PublicacionResponseDTO:
        publicacion = self._obtener_y_validar_autor(publicacion_id, usuario_id)
        publicacion_actualizada = self.repository.update(
            publicacion,
            publicacion_data,
        )
        return PublicacionMapper.to_response_dto(publicacion_actualizada)

    def delete(self, publicacion_id: int, usuario_id: int) -> None:
        publicacion = self._obtener_y_validar_autor(publicacion_id, usuario_id)
        self.repository.delete(publicacion)

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

    def _obtener_y_validar_autor(self, publicacion_id: int, usuario_id: int):
        publicacion = self.repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada.")

        if publicacion.autor_id != usuario_id:
            raise ForbiddenError(
                "Solo el autor puede modificar o eliminar la publicación."
            )

        return publicacion
