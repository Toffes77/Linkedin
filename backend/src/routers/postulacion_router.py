from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.postulacion_dto import (
    PostulacionResponseDTO,
)
from src.mappers.postulacion_mapper import PostulacionMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.postulacion_schema import (
    CreatePostulacionSchema,
    GetPostulacionSchema,
    UpdatePostulacionSchema,
)
from src.services.postulacion_service import PostulacionService

router = APIRouter(tags=["postulaciones"])


@router.post(
    "/postulaciones",
    response_model=GetPostulacionSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_postulacion(
    payload: CreatePostulacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = PostulacionMapper.to_create_dto(payload, current_user.id)
    postulacion: PostulacionResponseDTO = PostulacionService(db).create(dto)
    return PostulacionMapper.to_response_schema(postulacion)


@router.get("/ofertas/{oferta_id}/postulaciones", response_model=list[GetPostulacionSchema])
def get_postulaciones_by_oferta(
    oferta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    postulaciones: list[PostulacionResponseDTO] = PostulacionService(db).get_by_oferta(
        oferta_id,
        current_user.id,
    )
    return [PostulacionMapper.to_response_schema(postulacion) for postulacion in postulaciones]


@router.get("/usuarios/{usuario_id}/postulaciones", response_model=list[GetPostulacionSchema])
def get_postulaciones_by_usuario(usuario_id: int, db: Session = Depends(get_db)):
    postulaciones: list[PostulacionResponseDTO] = PostulacionService(db).get_by_usuario(
        usuario_id
    )
    return [PostulacionMapper.to_response_schema(postulacion) for postulacion in postulaciones]


@router.get("/postulaciones/{postulacion_id}", response_model=GetPostulacionSchema)
def get_postulacion(postulacion_id: int, db: Session = Depends(get_db)):
    postulacion: PostulacionResponseDTO = PostulacionService(db).get_by_id(
        postulacion_id
    )
    return PostulacionMapper.to_response_schema(postulacion)


@router.patch("/postulaciones/{postulacion_id}", response_model=GetPostulacionSchema)
def update_postulacion(
    postulacion_id: int,
    payload: UpdatePostulacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = PostulacionMapper.to_update_dto(payload)
    postulacion: PostulacionResponseDTO = PostulacionService(db).update(
        postulacion_id,
        dto,
        current_user.id,
    )
    return PostulacionMapper.to_response_schema(postulacion)
