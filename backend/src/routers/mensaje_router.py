from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.mappers.mensaje_mapper import MensajeMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.mensaje_schema import (
    CompartirPublicacionSchema,
    ContactoConversacionSchema,
    ConversacionSchema,
    CrearConversacionSchema,
    EnviarMensajeSchema,
    MensajeSchema,
    MensajesNoLeidosSchema,
)
from src.services.mensaje_service import MensajeService
from src.utils.openapi import error_responses

router = APIRouter(prefix="/conversaciones", tags=["mensajes"])


@router.get(
    "",
    response_model=list[ContactoConversacionSchema],
    summary="Listar contactos y conversaciones",
    description=(
        "Lista todos los contactos con conexión aceptada, incluso si todavía no "
        "existe una conversación, junto con último mensaje y no leídos."
    ),
    responses=error_responses(401),
)
def listar_conversaciones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    contactos = MensajeService(db).list_contacts(current_user.id)
    return [MensajeMapper.to_contact_schema(contacto) for contacto in contactos]


@router.post(
    "",
    response_model=ConversacionSchema,
    summary="Abrir o recuperar conversación",
    description=(
        "Obtiene la conversación única entre el usuario autenticado y otro contacto, "
        "creándola si no existe. Requiere una conexión aceptada."
    ),
    responses=error_responses(400, 401, 403, 404),
)
def abrir_conversacion(
    payload: CrearConversacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = MensajeMapper.to_create_conversation_dto(payload)
    conversacion = MensajeService(db).get_or_create(dto, current_user.id)
    return MensajeMapper.to_conversation_schema(conversacion)


@router.get(
    "/no-leidos/count",
    response_model=MensajesNoLeidosSchema,
    summary="Contar mensajes no leídos",
    description="Devuelve la cantidad total de mensajes no leídos del usuario autenticado.",
    responses=error_responses(401),
)
def contar_no_leidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return {"cantidad": MensajeService(db).count_unread(current_user.id)}


@router.get(
    "/{conversacion_id}/mensajes",
    response_model=list[MensajeSchema],
    summary="Listar mensajes",
    description="Lista mensajes de una conversación en orden paginado; el usuario debe participar en ella.",
    responses=error_responses(401, 403, 404),
)
def obtener_mensajes(
    conversacion_id: Annotated[int, Path(..., description="Conversación cuyos mensajes se consultan.")],
    limit: int = Query(default=30, ge=1, le=100, description="Cantidad de mensajes (1 a 100)."),
    offset: int = Query(default=0, ge=0, description="Cantidad de mensajes a omitir."),
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
    summary="Enviar mensaje",
    description="Envía un mensaje de texto de hasta 2000 caracteres a una conversación propia entre conexiones aceptadas.",
    responses=error_responses(400, 401, 403, 404),
)
def enviar_mensaje(
    conversacion_id: Annotated[int, Path(..., description="Conversación a la que se envía el mensaje.")],
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


@router.post(
    "/{conversacion_id}/mensajes/publicaciones",
    response_model=MensajeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Compartir publicación en conversación",
    description="Envía una publicación existente como mensaje compartido a una conversación propia.",
    responses=error_responses(401, 403, 404),
)
def compartir_publicacion(
    conversacion_id: Annotated[int, Path(..., description="Conversación a la que se comparte la publicación.")],
    payload: CompartirPublicacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = MensajeMapper.to_share_post_dto(payload)
    mensaje = MensajeService(db).share_post(
        conversacion_id,
        dto,
        current_user.id,
    )
    return MensajeMapper.to_message_schema(mensaje)


@router.post(
    "/{conversacion_id}/leer",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Marcar conversación como leída",
    description="Actualiza la marca ultima_lectura del usuario autenticado para esa conversación.",
    responses=error_responses(401, 403, 404),
)
def marcar_como_leida(
    conversacion_id: Annotated[int, Path(..., description="Conversación que se marca como leída.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    MensajeService(db).mark_as_read(conversacion_id, current_user.id)
