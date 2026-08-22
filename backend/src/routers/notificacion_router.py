from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.notificacion_dto import NotificacionResponseDTO
from src.mappers.notificacion_mapper import NotificacionMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.notificacion_schema import (
    NotificacionResponseSchema,
    NotificacionesNoLeidasSchema,
)
from src.services.notificacion_service import NotificacionService

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("", response_model=list[NotificacionResponseSchema])
def get_notificaciones(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    notifications: list[NotificacionResponseDTO] = NotificacionService(db).get_for_user(
        current_user.id, limit, offset
    )
    return [NotificacionMapper.to_response_schema(notification) for notification in notifications]


@router.get("/no-leidas/count", response_model=NotificacionesNoLeidasSchema)
def count_notificaciones_no_leidas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return {"cantidad": NotificacionService(db).count_unread(current_user.id)}


@router.patch("/{notificacion_id}/leida", response_model=NotificacionResponseSchema)
def marcar_notificacion_leida(
    notificacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    notification = NotificacionService(db).mark_as_read(notificacion_id, current_user.id)
    return NotificacionMapper.to_response_schema(notification)
