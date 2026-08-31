from fastapi import APIRouter, Depends, status
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

router = APIRouter(tags=["experiencias"])


@router.post(
    "/usuarios/{usuario_id}/experiencias",
    response_model=GetExperienciaSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_experiencia(
    usuario_id: int,
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
