from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.mappers.mensaje_mapper import MensajeMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.mensaje_schema import (
    ContactoConversacionSchema,
    ConversacionSchema,
    CrearConversacionSchema,
    EnviarMensajeSchema,
    MensajeSchema,
    MensajesNoLeidosSchema,
)
from src.services.mensaje_service import MensajeService

router = APIRouter(prefix="/conversaciones", tags=["mensajes"])


@router.get("", response_model=list[ContactoConversacionSchema])
def listar_conversaciones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    contactos = MensajeService(db).list_contacts(current_user.id)
    return [MensajeMapper.to_contact_schema(contacto) for contacto in contactos]


@router.post("", response_model=ConversacionSchema)
def abrir_conversacion(
    payload: CrearConversacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = MensajeMapper.to_create_conversation_dto(payload)
    conversacion = MensajeService(db).get_or_create(dto, current_user.id)
    return MensajeMapper.to_conversation_schema(conversacion)


@router.get("/no-leidos/count", response_model=MensajesNoLeidosSchema)
def contar_no_leidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return {"cantidad": MensajeService(db).count_unread(current_user.id)}


@router.get("/{conversacion_id}/mensajes", response_model=list[MensajeSchema])
def obtener_mensajes(
    conversacion_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    mensajes = MensajeService(db).get_messages(
        conversacion_id,
        current_user.id,
        limit,
        offset,
    )
    return [MensajeMapper.to_message_schema(message) for message in mensajes]


@router.post(
    "/{conversacion_id}/mensajes",
    response_model=MensajeSchema,
    status_code=status.HTTP_201_CREATED,
)
def enviar_mensaje(
    conversacion_id: int,
    payload: EnviarMensajeSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = MensajeMapper.to_send_message_dto(payload)
    mensaje = MensajeService(db).send_message(
        conversacion_id,
        dto,
        current_user.id,
    )
    return MensajeMapper.to_message_schema(mensaje)


@router.post("/{conversacion_id}/leer", status_code=status.HTTP_204_NO_CONTENT)
def marcar_como_leida(
    conversacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    MensajeService(db).mark_as_read(conversacion_id, current_user.id)

