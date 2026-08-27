from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.publicacion_dto import (
    PublicacionResponseDTO,
)
from src.mappers.publicacion_mapper import PublicacionMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.publicación_schemas import (
    CreatePublicacionSchema,
    GetPublicacionSchema,
    UpdatePublicacionSchema,
)
from src.services.publicacion_service import PublicacionService

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


@router.get("/autor/{usuario_id}", response_model=list[GetPublicacionSchema])
def get_publicaciones_por_autor(
    usuario_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    publicaciones = PublicacionService(db).get_by_autor(usuario_id, limit, offset)
    return [PublicacionMapper.to_response_schema(publicacion) for publicacion in publicaciones]


@router.post("", response_model=GetPublicacionSchema, status_code=status.HTTP_201_CREATED)
def create_publicacion(
    payload: CreatePublicacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = PublicacionMapper.to_create_dto(payload, current_user.id)
    publicacion: PublicacionResponseDTO = PublicacionService(db).create(dto)
    return PublicacionMapper.to_response_schema(publicacion)


@router.get("/{publicacion_id}", response_model=GetPublicacionSchema)
def get_publicacion(
    publicacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    publicacion = PublicacionService(db).get_by_id(publicacion_id)
    return PublicacionMapper.to_response_schema(publicacion)


@router.put("/{publicacion_id}", response_model=GetPublicacionSchema)
def update_publicacion(
    publicacion_id: int,
    payload: UpdatePublicacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = PublicacionMapper.to_update_dto(payload)
    publicacion: PublicacionResponseDTO = PublicacionService(db).update(
        publicacion_id,
        current_user.id,
        dto,
    )
    return PublicacionMapper.to_response_schema(publicacion)


@router.delete("/{publicacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publicacion(
    publicacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    PublicacionService(db).delete(publicacion_id, current_user.id)
