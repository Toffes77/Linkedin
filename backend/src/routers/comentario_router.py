from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.comentario_dto import ComentarioResponseDTO
from src.mappers.comentario_mapper import ComentarioMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.comentario_schema import (
    CantidadComentariosSchema,
    CrearComentarioSchema,
    GetComentarioSchema,
)
from src.schemas.pagination_schema import CursorPageSchema
from src.services.comentario_service import ComentarioService

router = APIRouter(tags=["comentarios"])


@router.post(
    "/publicaciones/{publicacion_id}/comentarios",
    response_model=GetComentarioSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_comentario(
    publicacion_id: int,
    payload: CrearComentarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    data = ComentarioMapper.to_create_dto(payload)
    comentario: ComentarioResponseDTO = ComentarioService(db).create(
        publicacion_id,
        data,
        current_user.id,
    )
    return ComentarioMapper.to_response_schema(comentario)


@router.post(
    "/comentarios/{comentario_id}/respuestas",
    response_model=GetComentarioSchema,
    status_code=status.HTTP_201_CREATED,
)
def reply_comentario(
    comentario_id: int,
    payload: CrearComentarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    data = ComentarioMapper.to_create_dto(payload)
    comentario: ComentarioResponseDTO = ComentarioService(db).reply(
        comentario_id,
        data,
        current_user.id,
    )
    return ComentarioMapper.to_response_schema(comentario)


@router.get(
    "/publicaciones/{publicacion_id}/comentarios",
    response_model=CursorPageSchema[GetComentarioSchema],
)
def get_comentarios(
    publicacion_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=2048),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    page = ComentarioService(db).list_roots(
        publicacion_id,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetComentarioSchema].model_validate(page)


@router.get(
    "/comentarios/{comentario_id}/respuestas",
    response_model=CursorPageSchema[GetComentarioSchema],
)
def get_respuestas(
    comentario_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=2048),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    page = ComentarioService(db).list_replies(
        comentario_id,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetComentarioSchema].model_validate(page)


@router.get(
    "/publicaciones/{publicacion_id}/comentarios/count",
    response_model=CantidadComentariosSchema,
)
def count_comentarios(
    publicacion_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    return CantidadComentariosSchema.model_validate(
        ComentarioService(db).count_by_publicacion(publicacion_id)
    )


@router.delete(
    "/comentarios/{comentario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comentario(
    comentario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ComentarioService(db).delete(comentario_id, current_user.id)
