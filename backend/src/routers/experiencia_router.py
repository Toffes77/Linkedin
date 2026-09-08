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
