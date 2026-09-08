from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.seguimiento_dto import SeguimientoResponseDTO
from src.mappers.seguimiento_mapper import SeguimientoMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.seguimiento_schema import (
    EstadoSeguimientoResponseSchema,
    SeguimientoResponseSchema,
)
from src.services.seguimiento_service import SeguimientoService
from src.utils.openapi import error_responses

router = APIRouter(prefix="/usuarios", tags=["seguimiento"])


@router.get(
    "/{usuario_id}/seguimiento",
    response_model=EstadoSeguimientoResponseSchema,
    summary="Consultar seguimiento",
    description="Indica si el usuario autenticado sigue al usuario indicado.",
    responses=error_responses(401, 404),
)
def get_estado_seguimiento(
    usuario_id: Annotated[int, Path(..., description="Usuario cuyo seguimiento se consulta.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estado = SeguimientoService(db).get_status(current_user.id, usuario_id)
    return SeguimientoMapper.to_status_schema(estado)


@router.post(
    "/{usuario_id}/seguir",
    response_model=SeguimientoResponseSchema,
    summary="Seguir usuario",
    description="Comienza a seguir al usuario indicado y genera una notificación para él.",
    responses=error_responses(401, 404, 409),
)
def seguir_usuario(
    usuario_id: Annotated[int, Path(..., description="Usuario que se quiere seguir.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    seguimiento: SeguimientoResponseDTO = SeguimientoService(db).follow(
        current_user.id, usuario_id
    )
    return SeguimientoMapper.to_response_schema(seguimiento)


@router.delete(
    "/{usuario_id}/seguir",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dejar de seguir usuario",
    description="Elimina el seguimiento del usuario indicado. Si no existía, la operación no tiene efecto.",
    responses=error_responses(401, 404),
)
def dejar_de_seguir_usuario(
    usuario_id: Annotated[int, Path(..., description="Usuario cuyo seguimiento se elimina.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    SeguimientoService(db).unfollow(current_user.id, usuario_id)
