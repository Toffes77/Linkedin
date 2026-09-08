from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.reacciones_dto import (
    ReaccionResponseDTO,
)
from src.mappers.reaccion_mapper import ReaccionMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.reaciones_schema import (
    CreateReaccionSchema,
    GetReaccionSchema,
    UpdateReaccionSchema,
)
from src.services.reacciones_service import ReaccionesService
from src.utils.openapi import error_responses

router = APIRouter(tags=["reacciones"])


@router.post(
    "/reacciones",
    response_model=GetReaccionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear reacción",
    description="Crea una reacción del usuario autenticado sobre una publicación; solo puede existir una por usuario y publicación.",
    responses=error_responses(401, 404, 409),
)
def create_reaccion(
    payload: CreateReaccionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ReaccionMapper.to_create_dto(payload, current_user.id)
    reaccion: ReaccionResponseDTO = ReaccionesService(db).create(dto)
    return ReaccionMapper.to_response_schema(reaccion)


@router.patch(
    "/publicaciones/{publicacion_id}/reacciones",
    response_model=GetReaccionSchema,
    summary="Cambiar mi reacción",
    description="Cambia el tipo de la reacción existente del usuario autenticado sobre una publicación.",
    responses=error_responses(401, 404),
)
def update_reaccion(
    publicacion_id: Annotated[int, Path(..., description="Publicación cuya reacción propia se actualiza.")],
    payload: UpdateReaccionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ReaccionMapper.to_update_dto(payload)
    reaccion: ReaccionResponseDTO = ReaccionesService(db).update(
        current_user.id,
        publicacion_id,
        dto,
    )
    return ReaccionMapper.to_response_schema(reaccion)


@router.get(
    "/publicaciones/{publicacion_id}/reacciones/me",
    response_model=GetReaccionSchema | None,
    summary="Obtener mi reacción",
    description="Devuelve la reacción del usuario autenticado o null si todavía no reaccionó.",
    responses=error_responses(401, 404),
)
def get_mi_reaccion(
    publicacion_id: Annotated[int, Path(..., description="Publicación cuya reacción se consulta.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    reaccion = ReaccionesService(db).get_optional_by_usuario_and_publicacion(
        current_user.id,
        publicacion_id,
    )
    if reaccion is None:
        return None
    return ReaccionMapper.to_response_schema(reaccion)


@router.delete(
    "/publicaciones/{publicacion_id}/reacciones/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mi reacción",
    description="Elimina la reacción propia; si no existe, la operación no tiene efecto.",
    responses=error_responses(401, 404),
)
def delete_mi_reaccion(
    publicacion_id: Annotated[int, Path(..., description="Publicación de la reacción propia.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ReaccionesService(db).delete(current_user.id, publicacion_id)


@router.get(
    "/publicaciones/{publicacion_id}/reacciones",
    response_model=dict[str, int],
    summary="Contar reacciones",
    description="Devuelve los conteos por tipo (like, celebrar, apoyar e interesante). No requiere autenticación.",
    responses=error_responses(404),
)
def get_reacciones_count(
    publicacion_id: Annotated[int, Path(..., description="Publicación cuyos conteos se consultan.")],
    db: Session = Depends(get_db),
):
    return ReaccionesService(db).get_counts_by_publicacion(publicacion_id)
