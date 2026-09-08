from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    EstadoConexionResponseDTO,
)
from src.mappers.conexion_mapper import ConexionMapper
from src.schemas.conexiones_schema import (
    CreateConexionSchema,
    EstadoConexionResponseSchema,
    GetConexionSchema,
    UpdateConexionSchema,
    ResumenRedResponseSchema,
    InvitacionRecibidaResponseSchema,
)
from src.middlewares.auth_middleware import get_current_user
from src.services.conexion_service import ConexionService
from src.utils.openapi import error_responses

router = APIRouter(prefix="/conexiones", tags=["conexiones"])


@router.get(
    "/resumen",
    response_model=ResumenRedResponseSchema,
    summary="Obtener resumen de red",
    description="Devuelve contadores de invitaciones enviadas, contactos aceptados y usuarios seguidos.",
    responses=error_responses(401),
)
def get_resumen_red(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    resumen = ConexionService(db).get_resumen_red(current_user.id)
    return ConexionMapper.to_resumen_response_schema(resumen)


@router.get(
    "/invitaciones-recibidas",
    response_model=list[InvitacionRecibidaResponseSchema],
    summary="Listar invitaciones recibidas",
    description="Lista las solicitudes de conexión pendientes recibidas por el usuario autenticado.",
    responses=error_responses(401),
)
def get_invitaciones_recibidas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    invitations = ConexionService(db).get_invitaciones_recibidas(current_user.id)
    return [
        ConexionMapper.to_invitacion_response_schema(invitation)
        for invitation in invitations
    ]


@router.get(
    "/estado/{usuario_id}",
    response_model=EstadoConexionResponseSchema,
    summary="Consultar estado de conexión",
    description=(
        "Indica si la relación está sin conexión, pendiente enviada/recibida, "
        "aceptada o rechazada."
    ),
    responses=error_responses(401, 404),
)
def get_estado_conexion(
    usuario_id: Annotated[int, Path(..., description="Otro usuario cuya relación se consulta.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estado: EstadoConexionResponseDTO = ConexionService(db).get_estado(
        current_user.id,
        usuario_id,
    )
    return ConexionMapper.to_estado_response_schema(estado)


@router.post(
    "",
    response_model=GetConexionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar invitación de conexión",
    description=(
        "Crea una invitación desde usuario_a hacia usuario_b. usuario_a debe "
        "coincidir con la identidad autenticada; no se permiten auto-invitaciones "
        "ni relaciones duplicadas."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def create_conexion(
    payload: CreateConexionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ConexionMapper.to_create_dto(payload)
    conexion: ConexionResponseDTO = ConexionService(db).create(dto, current_user.id)
    return ConexionMapper.to_response_schema(conexion)


@router.patch(
    "/{usuario_a}/{usuario_b}",
    response_model=GetConexionSchema,
    summary="Responder invitación de conexión",
    description=(
        "Acepta o rechaza una solicitud pendiente. Solo el destinatario puede "
        "responderla; aceptar genera la notificación correspondiente."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def update_conexion(
    usuario_a: Annotated[int, Path(..., description="Primer usuario de la relación.")],
    usuario_b: Annotated[int, Path(..., description="Segundo usuario de la relación.")],
    payload: UpdateConexionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ConexionMapper.to_update_dto(payload)
    conexion: ConexionResponseDTO = ConexionService(db).update(
        usuario_a,
        usuario_b,
        dto,
        current_user.id,
    )
    return ConexionMapper.to_response_schema(conexion)


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desconectar usuario",
    description="Elimina una conexión aceptada entre el usuario autenticado y el usuario indicado.",
    responses=error_responses(401, 404, 409),
)
def delete_conexion(
    usuario_id: Annotated[int, Path(..., description="Usuario con el que se termina la conexión.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ConexionService(db).delete(usuario_id, current_user.id)
