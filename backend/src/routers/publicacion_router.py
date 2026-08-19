from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.publicacion_dto import (
    CreatePublicacionDTO,
    PublicacionResponseDTO,
    UpdatePublicacionDTO,
)
from src.middlewares.auth_middleware import get_current_user
from src.schemas.publicación_schemas import (
    CreatePublicacionSchema,
    GetPublicacionSchema,
    UpdatePublicacionSchema,
)
from src.services.publicacion_service import PublicacionService

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


@router.post("", response_model=GetPublicacionSchema, status_code=status.HTTP_201_CREATED)
def create_publicacion(
    payload: CreatePublicacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreatePublicacionDTO(autor_id=current_user.id, **payload.model_dump())
    publicacion: PublicacionResponseDTO = PublicacionService(db).create(dto)
    return GetPublicacionSchema.model_validate(publicacion)


@router.put("/{publicacion_id}", response_model=GetPublicacionSchema)
def update_publicacion(
    publicacion_id: int,
    payload: UpdatePublicacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdatePublicacionDTO(**payload.model_dump(exclude_unset=True))
    publicacion: PublicacionResponseDTO = PublicacionService(db).update(
        publicacion_id,
        current_user.id,
        dto,
    )
    return GetPublicacionSchema.model_validate(publicacion)


@router.delete("/{publicacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publicacion(
    publicacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    PublicacionService(db).delete(publicacion_id, current_user.id)
