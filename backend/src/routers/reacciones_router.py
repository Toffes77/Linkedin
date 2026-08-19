from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.reacciones_dto import (
    CreateReaccionDTO,
    ReaccionResponseDTO,
    UpdateReaccionDTO,
)
from src.middlewares.auth_middleware import get_current_user
from src.schemas.reaciones_schema import (
    CreateReaccionSchema,
    GetReaccionSchema,
    UpdateReaccionSchema,
)
from src.services.reacciones_service import ReaccionesService

router = APIRouter(tags=["reacciones"])


@router.post(
    "/reacciones",
    response_model=GetReaccionSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_reaccion(
    payload: CreateReaccionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreateReaccionDTO(
        usuario_id=current_user.id,
        publicacion_id=payload.publicacion_id,
        tipo=payload.tipo,
    )
    reaccion: ReaccionResponseDTO = ReaccionesService(db).create(dto)
    return GetReaccionSchema.model_validate(reaccion)


@router.patch(
    "/publicaciones/{publicacion_id}/reacciones",
    response_model=GetReaccionSchema,
)
def update_reaccion(
    publicacion_id: int,
    payload: UpdateReaccionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdateReaccionDTO(**payload.model_dump())
    reaccion: ReaccionResponseDTO = ReaccionesService(db).update(
        current_user.id,
        publicacion_id,
        dto,
    )
    return GetReaccionSchema.model_validate(reaccion)


@router.get("/publicaciones/{publicacion_id}/reacciones", response_model=dict[str, int])
def get_reacciones_count(publicacion_id: int, db: Session = Depends(get_db)):
    return ReaccionesService(db).get_counts_by_publicacion(publicacion_id)
