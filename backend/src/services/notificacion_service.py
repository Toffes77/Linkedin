from sqlalchemy.orm import Session

from src.dtos.notificacion_dto import CreateNotificacionDTO, NotificacionResponseDTO
from src.mappers.notificacion_mapper import NotificacionMapper
from src.repositories.notificacion_repository import NotificacionRepository
from src.utils.errors import ForbiddenError, NotFoundError


class NotificacionService:
    def __init__(self, db: Session):
        self.repository = NotificacionRepository(db)

    def create_many(
        self,
        notifications: list[CreateNotificacionDTO],
        *,
        commit: bool = True,
    ) -> None:
        self.repository.create_many(notifications, commit=commit)

    def get_for_user(
        self, usuario_id: int, limit: int = 30, offset: int = 0
    ) -> list[NotificacionResponseDTO]:
        return [
            NotificacionMapper.to_response_dto(notification)
            for notification in self.repository.get_by_user(usuario_id, limit, offset)
        ]

    def mark_as_read(
        self, notificacion_id: int, usuario_id: int
    ) -> NotificacionResponseDTO:
        notification = self.repository.get_by_id(notificacion_id)
        if notification is None:
            raise NotFoundError("Notificación no encontrada.")
        if notification.usuario_id != usuario_id:
            raise ForbiddenError("No puede modificar una notificación de otro usuario.")
        return NotificacionMapper.to_response_dto(
            self.repository.mark_as_read(notification)
        )

    def count_unread(self, usuario_id: int) -> int:
        return self.repository.count_unread(usuario_id)
