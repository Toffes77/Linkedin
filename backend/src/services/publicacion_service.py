from sqlalchemy.orm import Session

from src.dtos.publicacion_dto import (
    CreatePublicacionDTO,
    PublicacionResponseDTO,
    UpdatePublicacionDTO,
)
from src.mappers.publicacion_mapper import PublicacionMapper
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ForbiddenError, NotFoundError


class PublicacionService:
    def __init__(self, db: Session):
        self.repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)

    def create(
        self,
        publicacion_data: CreatePublicacionDTO,
    ) -> PublicacionResponseDTO:
        self._validar_usuario(publicacion_data.autor_id)

        publicacion = self.repository.create(publicacion_data)
        return PublicacionMapper.to_response_dto(publicacion)

    def get_by_id(self, publicacion_id: int) -> PublicacionResponseDTO:
        publicacion = self.repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada.")

        return PublicacionMapper.to_response_dto(publicacion)

    def get_by_autor(self, autor_id: int) -> list[PublicacionResponseDTO]:
        self._validar_usuario(autor_id)
        publicaciones = self.repository.get_by_autor(autor_id)
        return [PublicacionMapper.to_response_dto(publicacion) for publicacion in publicaciones]

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
