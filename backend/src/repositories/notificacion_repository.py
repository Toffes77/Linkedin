from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models.notificacion_model import Notificacion
from src.dtos.notificacion_dto import CreateNotificacionDTO
from src.mappers.notificacion_mapper import NotificacionMapper


class NotificacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(
        self,
        notifications: list[CreateNotificacionDTO],
        *,
        commit: bool = True,
    ) -> list[Notificacion]:
        models = [NotificacionMapper.to_model(notification) for notification in notifications]
        if not models:
            return []
        self.db.add_all(models)
        if commit:
            self.db.commit()
            for model in models:
                self.db.refresh(model)
        else:
            self.db.flush()
        return models

    def get_by_user(self, usuario_id: int, limit: int, offset: int) -> list[Notificacion]:
        return (
            self.db.query(Notificacion)
            .filter(Notificacion.usuario_id == usuario_id)
            .order_by(Notificacion.fecha.desc(), Notificacion.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_id(self, notificacion_id: int) -> Notificacion | None:
        return self.db.get(Notificacion, notificacion_id)

    def mark_as_read(self, notificacion: Notificacion) -> Notificacion:
        notificacion.leida = True
        self.db.commit()
        self.db.refresh(notificacion)
        return notificacion

    def count_unread(self, usuario_id: int) -> int:
        return (
            self.db.query(func.count(Notificacion.id))
            .filter(Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False))
            .scalar()
        )
