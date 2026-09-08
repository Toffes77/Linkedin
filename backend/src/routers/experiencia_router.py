from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.experiencia_dto import (
    ExperienciaResponseDTO,
)
from src.mappers.experiencia_mapper import ExperienciaMapper
from src.schemas.experiencia_schema import (
    CreateExperienciaSchema,
    GetExperienciaSchema,
    UpdateExperienciaSchema,
)
from src.middlewares.auth_middleware import get_current_user
from src.services.experiencia_service import ExperienciaService
from src.utils.openapi import error_responses

router = APIRouter(tags=["experiencias"])


@router.post(
    "/usuarios/{usuario_id}/experiencias",
    response_model=GetExperienciaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar experiencia laboral",
    description=(
        "Agrega una experiencia al perfil del usuario autenticado. Solo se puede "
        "modificar el propio perfil; la empresa debe existir y no puede haber "
        "períodos solapados para la misma empresa."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def create_experiencia(
    usuario_id: Annotated[int, Path(..., description="Usuario cuyo perfil recibe la experiencia.")],
    payload: CreateExperienciaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ExperienciaMapper.to_create_dto(payload, usuario_id)
    experiencia: ExperienciaResponseDTO = ExperienciaService(db).create(
        dto,
        current_user.id,
    )
    return ExperienciaMapper.to_response_schema(experiencia)


@router.put(
    "/experiencias/{experiencia_id}",
    response_model=GetExperienciaSchema,
    summary="Editar experiencia laboral",
    description=(
        "Actualiza una experiencia del usuario autenticado. Solo su propietario "
        "puede modificarla; la empresa debe existir y el período no puede "
        "solaparse con otra experiencia en la misma empresa."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def update_experiencia(
    experiencia_id: Annotated[int, Path(..., description="Experiencia propia que se actualiza.")],
    payload: UpdateExperienciaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    experiencia = ExperienciaService(db).update(
        experiencia_id,
        ExperienciaMapper.to_update_dto(payload),
        current_user.id,
    )
    return ExperienciaMapper.to_response_schema(experiencia)


@router.delete(
    "/experiencias/{experiencia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar experiencia laboral",
    description="Elimina una experiencia. Solo el propietario autenticado puede hacerlo.",
    responses=error_responses(401, 403, 404),
)
def delete_experiencia(
    experiencia_id: Annotated[int, Path(..., description="Experiencia propia que se elimina.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ExperienciaService(db).delete(experiencia_id, current_user.id)
