from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile, status
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
from src.utils.openapi import error_responses

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


@router.get(
    "/autor/{usuario_id}",
    response_model=list[GetPublicacionCardSchema],
    summary="Listar publicaciones de un autor",
    description=(
        "Lista publicaciones de un usuario con paginación offset. Es público; "
        "si se envía autenticación, las tarjetas incluyen la reacción propia."
    ),
    responses=error_responses(401, 404),
)
def get_publicaciones_por_autor(
    usuario_id: Annotated[int, Path(..., description="Autor cuyas publicaciones se consultan.")],
    limit: int = Query(default=20, ge=1, le=100, description="Cantidad de resultados (1 a 100)."),
    offset: int = Query(default=0, ge=0, description="Cantidad de resultados a omitir.") ,
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


@router.post(
    "",
    response_model=GetPublicacionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear publicación de texto",
    description="Crea una publicación de texto para el usuario autenticado.",
    responses=error_responses(401, 404),
)
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
    summary="Crear publicación con multimedia",
    description=(
        "Crea una publicación con texto, imágenes, videos o una combinación. "
        "Admite hasta 10 archivos y 150 MiB totales; cada imagen admite 5 MiB "
        "y cada video 50 MiB. Debe existir texto o al menos un archivo."
    ),
    responses=error_responses(400, 401, 404),
)
async def create_publicacion_multimedia(
    texto: str = Form(
        default="",
        max_length=3000,
        description="Texto opcional; máximo 3000 caracteres si se envía multimedia.",
    ),
    archivos: list[UploadFile] | None = File(
        default=None,
        description=(
            "Archivos JPG/JPEG/PNG/WEBP, MP4 o WEBM; hasta 10 archivos y 150 MiB totales."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreatePublicacionMultimediaDTO(autor_id=current_user.id, texto=texto)
    uploads = await read_publication_uploads(archivos or [])
    publicacion = PublicacionService(db).create_with_multimedia(dto, uploads)
    return PublicacionMapper.to_response_schema(publicacion)


@router.get(
    "/{publicacion_id}",
    response_model=GetPublicacionCardSchema,
    summary="Obtener detalle de publicación",
    description=(
        "Devuelve una publicación enriquecida con autor, multimedia, reacciones y "
        "cantidad de comentarios. Requiere autenticación para calcular la reacción propia."
    ),
    responses=error_responses(401, 404),
)
def get_publicacion(
    publicacion_id: Annotated[int, Path(..., description="Publicación que se consulta.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    publicacion = PublicacionService(db).get_by_id(publicacion_id, current_user.id)
    return PublicacionMapper.to_card_schema(publicacion)


@router.put(
    "/{publicacion_id}",
    response_model=GetPublicacionSchema,
    summary="Editar publicación de texto",
    description="Actualiza el texto de una publicación. Solo el autor puede editarla.",
    responses=error_responses(401, 403, 404),
)
def update_publicacion(
    publicacion_id: Annotated[int, Path(..., description="Publicación propia que se actualiza.")],
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


@router.put(
    "/{publicacion_id}/multimedia",
    response_model=GetPublicacionSchema,
    summary="Editar publicación y multimedia",
    description=(
        "Reemplaza el texto y sincroniza los archivos de una publicación propia. "
        "conservar_multimedia_id identifica archivos existentes que se mantienen; "
        "el total no puede superar 10 archivos ni 150 MiB."
    ),
    responses=error_responses(400, 401, 403, 404),
)
async def update_publicacion_multimedia(
    publicacion_id: Annotated[int, Path(..., description="Publicación propia que se actualiza.")],
    texto: str = Form(default="", max_length=3000, description="Texto nuevo; puede quedar vacío si se conservan o agregan archivos."),
    conservar_multimedia_id: list[int] | None = Form(
        default=None,
        description="IDs de archivos existentes que deben conservarse.",
    ),
    archivos: list[UploadFile] | None = File(
        default=None,
        description="Archivos nuevos JPG/JPEG/PNG/WEBP, MP4 o WEBM.",
    ),
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


@router.delete(
    "/{publicacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar publicación",
    description="Elimina una publicación propia y sus archivos multimedia administrados.",
    responses=error_responses(401, 403, 404),
)
def delete_publicacion(
    publicacion_id: Annotated[int, Path(..., description="Publicación propia que se elimina.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    PublicacionService(db).delete(publicacion_id, current_user.id)
