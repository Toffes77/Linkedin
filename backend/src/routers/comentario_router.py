from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
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
from src.utils.openapi import error_responses

router = APIRouter(tags=["comentarios"])


@router.post(
    "/publicaciones/{publicacion_id}/comentarios",
    response_model=GetComentarioSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear comentario",
    description="Agrega un comentario raíz a una publicación existente; el contenido no puede estar vacío y admite hasta 1000 caracteres.",
    responses=error_responses(400, 401, 404),
)
def create_comentario(
    publicacion_id: Annotated[int, Path(..., description="Publicación que recibe el comentario.")],
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
    summary="Responder comentario",
    description="Crea una respuesta directa a un comentario existente de la misma publicación.",
    responses=error_responses(400, 401, 404),
)
def reply_comentario(
    comentario_id: Annotated[int, Path(..., description="Comentario al que se responde.")],
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
    summary="Listar comentarios raíz",
    description="Lista los comentarios raíz de una publicación con paginación por cursor.",
    responses=error_responses(400, 401, 404),
)
def get_comentarios(
    publicacion_id: Annotated[int, Path(..., description="Publicación cuyos comentarios se consultan.")],
    limit: int = Query(default=10, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
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
    summary="Listar respuestas",
    description="Lista las respuestas directas de un comentario con paginación por cursor.",
    responses=error_responses(400, 401, 404),
)
def get_respuestas(
    comentario_id: Annotated[int, Path(..., description="Comentario cuyas respuestas se consultan.")],
    limit: int = Query(default=10, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
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
    summary="Contar comentarios",
    description="Devuelve el total de comentarios, incluyendo comentarios raíz y respuestas, de una publicación.",
    responses=error_responses(401, 404),
)
def count_comentarios(
    publicacion_id: Annotated[int, Path(..., description="Publicación cuyo total se consulta.")],
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    return CantidadComentariosSchema.model_validate(
        ComentarioService(db).count_by_publicacion(publicacion_id)
    )


@router.delete(
    "/comentarios/{comentario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar comentario",
    description="Elimina un comentario propio. Solo el autor puede eliminarlo.",
    responses=error_responses(401, 403, 404),
)
def delete_comentario(
    comentario_id: Annotated[int, Path(..., description="Comentario propio que se elimina.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    ComentarioService(db).delete(comentario_id, current_user.id)
