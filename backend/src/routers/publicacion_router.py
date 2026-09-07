from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.publicacion_dto import (
    CreatePublicacionMultimediaDTO,
    PublicacionResponseDTO,
    UpdatePublicacionMultimediaDTO,
)
from src.mappers.publicacion_mapper import PublicacionMapper
from src.middlewares.auth_middleware import get_current_user, get_optional_current_user
from src.schemas.publicación_schemas import (
    CreatePublicacionSchema,
    GetPublicacionCardSchema,
    GetPublicacionSchema,
    UpdatePublicacionSchema,
)
from src.services.publicacion_service import PublicacionService
from src.utils.publication_media_storage import read_publication_uploads

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


@router.get("/autor/{usuario_id}", response_model=list[GetPublicacionCardSchema])
def get_publicaciones_por_autor(
    usuario_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario | None = Depends(get_optional_current_user),
):
    publicaciones = PublicacionService(db).get_by_autor(
        usuario_id,
        limit,
        offset,
        current_user.id if current_user else None,
    )
    return [PublicacionMapper.to_card_schema(publicacion) for publicacion in publicaciones]


@router.post("", response_model=GetPublicacionSchema, status_code=status.HTTP_201_CREATED)
def create_publicacion(
    payload: CreatePublicacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = PublicacionMapper.to_create_dto(payload, current_user.id)
    publicacion: PublicacionResponseDTO = PublicacionService(db).create(dto)
    return PublicacionMapper.to_response_schema(publicacion)


@router.post(
    "/multimedia",
    response_model=GetPublicacionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_publicacion_multimedia(
    texto: str = Form(default="", max_length=3000),
    archivos: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreatePublicacionMultimediaDTO(autor_id=current_user.id, texto=texto)
    uploads = await read_publication_uploads(archivos or [])
    publicacion = PublicacionService(db).create_with_multimedia(dto, uploads)
    return PublicacionMapper.to_response_schema(publicacion)


@router.get("/{publicacion_id}", response_model=GetPublicacionCardSchema)
def get_publicacion(
    publicacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    publicacion = PublicacionService(db).get_by_id(publicacion_id, current_user.id)
    return PublicacionMapper.to_card_schema(publicacion)


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


@router.put("/{publicacion_id}/multimedia", response_model=GetPublicacionSchema)
async def update_publicacion_multimedia(
    publicacion_id: int,
    texto: str = Form(default="", max_length=3000),
    conservar_multimedia_id: list[int] | None = Form(default=None),
    archivos: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdatePublicacionMultimediaDTO(texto=texto)
    uploads = await read_publication_uploads(archivos or [])
    publicacion = PublicacionService(db).update_with_multimedia(
        publicacion_id,
        current_user.id,
        dto,
        conservar_multimedia_id or [],
        uploads,
    )
    return PublicacionMapper.to_response_schema(publicacion)


@router.delete("/{publicacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publicacion(
    publicacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    PublicacionService(db).delete(publicacion_id, current_user.id)
