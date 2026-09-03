from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models.reaciones_model import REACCIONES_UNIQUE_CONSTRAINT
from src.dtos.reacciones_dto import (
    CreateReaccionDTO,
    ReaccionResponseDTO,
    UpdateReaccionDTO,
)
from src.mappers.reaccion_mapper import ReaccionMapper
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.reacciones_repository import ReaccionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, NotFoundError
from src.utils.integrity import violates_constraint


class ReaccionesService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ReaccionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.publicacion_repository = PublicacionRepository(db)

    def create(self, reaccion_data: CreateReaccionDTO) -> ReaccionResponseDTO:
        self._validar_usuario(reaccion_data.usuario_id)
        self._validar_publicacion(reaccion_data.publicacion_id)

        if (
            self.repository.get_by_usuario_and_publicacion(
                reaccion_data.usuario_id,
                reaccion_data.publicacion_id,
            )
            is not None
        ):
            raise ConflictError("El usuario ya reaccionó a esta publicación.")

        try:
            reaccion = self.repository.create(reaccion_data)
        except IntegrityError as exc:
            self.db.rollback()
            if violates_constraint(exc, REACCIONES_UNIQUE_CONSTRAINT):
                raise ConflictError(
                    "El usuario ya reaccionó a esta publicación."
                ) from exc
            raise
        return ReaccionMapper.to_response_dto(reaccion)

    def get_optional_by_usuario_and_publicacion(
        self,
        usuario_id: int,
        publicacion_id: int,
    ) -> ReaccionResponseDTO | None:
        self._validar_publicacion(publicacion_id)
        reaccion = self.repository.get_by_usuario_and_publicacion(
            usuario_id,
            publicacion_id,
        )
        if reaccion is None:
            return None
        return ReaccionMapper.to_response_dto(reaccion)

    def get_by_usuario_and_publicacion(
        self,
        usuario_id: int,
        publicacion_id: int,
    ) -> ReaccionResponseDTO:
        reaccion = self.repository.get_by_usuario_and_publicacion(
            usuario_id,
            publicacion_id,
        )
        if reaccion is None:
            raise NotFoundError("Reacción no encontrada.")

        return ReaccionMapper.to_response_dto(reaccion)

    def get_by_publicacion(
        self,
        publicacion_id: int,
    ) -> list[ReaccionResponseDTO]:
        self._validar_publicacion(publicacion_id)
        reacciones = self.repository.get_by_publicacion(publicacion_id)
        return [ReaccionMapper.to_response_dto(reaccion) for reaccion in reacciones]

    def update(
        self,
        usuario_id: int,
        publicacion_id: int,
        reaccion_data: UpdateReaccionDTO,
    ) -> ReaccionResponseDTO:
        reaccion = self.repository.get_by_usuario_and_publicacion(
            usuario_id,
            publicacion_id,
        )
        if reaccion is None:
            raise NotFoundError("Reacción no encontrada.")

        reaccion_actualizada = self.repository.update(reaccion, reaccion_data)
        return ReaccionMapper.to_response_dto(reaccion_actualizada)

    def delete(self, usuario_id: int, publicacion_id: int) -> None:
        self._validar_publicacion(publicacion_id)
        reaccion = self.repository.get_by_usuario_and_publicacion(
            usuario_id,
            publicacion_id,
        )
        if reaccion is None:
            return

        self.repository.delete(reaccion)

    def get_counts_by_publicacion(self, publicacion_id: int) -> dict[str, int]:
        self._validar_publicacion(publicacion_id)
        counts = {
            "like": 0,
            "celebrar": 0,
            "apoyar": 0,
            "interesante": 0,
        }
        for _, tipo, cantidad, _ in self.repository.summarize_by_publicaciones(
            [publicacion_id],
            None,
        ):
            counts[tipo] = cantidad
        return counts

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

    def _validar_publicacion(self, publicacion_id: int) -> None:
        if self.publicacion_repository.get_by_id(publicacion_id) is None:
            raise NotFoundError("Publicación no encontrada.")
