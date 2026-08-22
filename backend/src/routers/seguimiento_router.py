from fastapi import APIRouter, Depends, status
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

router = APIRouter(prefix="/usuarios", tags=["seguimiento"])


@router.get("/{usuario_id}/seguimiento", response_model=EstadoSeguimientoResponseSchema)
def get_estado_seguimiento(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estado = SeguimientoService(db).get_status(current_user.id, usuario_id)
    return SeguimientoMapper.to_status_schema(estado)


@router.post("/{usuario_id}/seguir", response_model=SeguimientoResponseSchema)
def seguir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    seguimiento: SeguimientoResponseDTO = SeguimientoService(db).follow(
        current_user.id, usuario_id
    )
    return SeguimientoMapper.to_response_schema(seguimiento)


@router.delete("/{usuario_id}/seguir", status_code=status.HTTP_204_NO_CONTENT)
def dejar_de_seguir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    SeguimientoService(db).unfollow(current_user.id, usuario_id)
