from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models.seguimiento_model import SEGUIMIENTO_UNIQUE_CONSTRAINT
from src.dtos.notificacion_dto import CreateNotificacionDTO
from src.dtos.seguimiento_dto import (
    EstadoSeguimientoResponseDTO,
    SeguimientoResponseDTO,
)
from src.mappers.seguimiento_mapper import SeguimientoMapper
from src.repositories.seguimiento_repository import SeguimientoRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.services.notificacion_service import NotificacionService
from src.utils.errors import ConflictError, NotFoundError
from src.utils.integrity import violates_constraint


class SeguimientoService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SeguimientoRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.notificacion_service = NotificacionService(db)

    def follow(self, seguidor_id: int, seguido_id: int) -> SeguimientoResponseDTO:
        self._validar_destino(seguidor_id, seguido_id)
        seguimiento = self.repository.get(seguidor_id, seguido_id)
        if seguimiento is not None:
            raise ConflictError("Ya sigue a este usuario.")

        seguidor = self._obtener_usuario(seguidor_id)
        try:
            seguimiento = self.repository.create(
                seguidor_id,
                seguido_id,
                commit=False,
            )
            self.notificacion_service.create_many(
                [
                    CreateNotificacionDTO(
                        usuario_id=seguido_id,
                        tipo="NUEVO_SEGUIDOR",
                        mensaje=f"{seguidor.nombre} empezó a seguirte.",
                        usuario_origen_id=seguidor_id,
                    )
                ],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(seguimiento)
        except IntegrityError as exc:
            self.db.rollback()
            if violates_constraint(exc, SEGUIMIENTO_UNIQUE_CONSTRAINT):
                raise ConflictError("Ya sigue a este usuario.") from exc
            raise
        except Exception:
            self.db.rollback()
            raise
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
        self._obtener_usuario(usuario_id)

    def _obtener_usuario(self, usuario_id: int):
        usuario = self.usuario_repository.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        return usuario
