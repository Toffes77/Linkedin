from sqlalchemy.orm import Session

from src.dtos.seguimiento_dto import (
    EstadoSeguimientoResponseDTO,
    SeguimientoResponseDTO,
)
from src.mappers.seguimiento_mapper import SeguimientoMapper
from src.repositories.seguimiento_repository import SeguimientoRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, NotFoundError


class SeguimientoService:
    def __init__(self, db: Session):
        self.repository = SeguimientoRepository(db)
        self.usuario_repository = UsuarioRepository(db)

    def follow(self, seguidor_id: int, seguido_id: int) -> SeguimientoResponseDTO:
        self._validar_destino(seguidor_id, seguido_id)
        seguimiento = self.repository.get(seguidor_id, seguido_id)
        if seguimiento is None:
            seguimiento = self.repository.create(seguidor_id, seguido_id)
        return SeguimientoMapper.to_response_dto(seguimiento)

    def unfollow(self, seguidor_id: int, seguido_id: int) -> None:
        self._validar_usuario(seguido_id)
        seguimiento = self.repository.get(seguidor_id, seguido_id)
        if seguimiento is not None:
            self.repository.delete(seguimiento)

    def get_status(
        self, seguidor_id: int, seguido_id: int
    ) -> EstadoSeguimientoResponseDTO:
        self._validar_usuario(seguido_id)
        return EstadoSeguimientoResponseDTO(
            siguiendo=self.repository.get(seguidor_id, seguido_id) is not None
        )

    def _validar_destino(self, seguidor_id: int, seguido_id: int) -> None:
        self._validar_usuario(seguido_id)
        if seguidor_id == seguido_id:
            raise ConflictError("No se puede seguir a uno mismo.")

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")
