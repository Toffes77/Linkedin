from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.experiencia_dto import (
    CreateExperienciaDTO,
    ExperienciaResponseDTO,
)
from src.schemas.experiencia_schema import (
    CreateExperienciaSchema,
    GetExperienciaSchema,
)
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
):
    dto = CreateExperienciaDTO(usuario_id=usuario_id, **payload.model_dump())
    experiencia: ExperienciaResponseDTO = ExperienciaService(db).create(dto)
    return GetExperienciaSchema.model_validate(experiencia)
