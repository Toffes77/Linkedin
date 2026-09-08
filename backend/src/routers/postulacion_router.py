from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
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
from src.schemas.pagination_schema import CursorPageSchema
from src.services.postulacion_service import PostulacionService
from src.utils.openapi import error_responses

router = APIRouter(tags=["postulaciones"])


@router.post(
    "/postulaciones",
    response_model=GetPostulacionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear postulación",
    description=(
        "Postula al usuario autenticado a una oferta publicada. El body solo recibe "
        "oferta_id: la identidad postulante se obtiene del JWT o cookie de sesión. "
        "No puede postularse a ofertas de una empresa a la que ya pertenece ni más "
        "de una vez a la misma oferta."
    ),
    responses=error_responses(401, 404, 409),
)
def create_postulacion(
    payload: CreatePostulacionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = PostulacionMapper.to_create_dto(payload, current_user.id)
    postulacion: PostulacionResponseDTO = PostulacionService(db).create(dto)
    return PostulacionMapper.to_response_schema(postulacion)


@router.get(
    "/ofertas/{oferta_id}/postulaciones",
    response_model=CursorPageSchema[GetPostulacionSchema],
    summary="Listar postulaciones de una oferta",
    description="Lista postulaciones de una oferta con cursor. Solo OWNER o RECRUITER de la empresa pueden acceder.",
    responses=error_responses(400, 401, 403, 404),
)
def get_postulaciones_by_oferta(
    oferta_id: Annotated[int, Path(..., description="Oferta cuyas postulaciones se consultan.")],
    limit: int = Query(default=20, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    page = PostulacionService(db).get_by_oferta(
        oferta_id,
        current_user.id,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetPostulacionSchema].model_validate(page)


@router.get(
    "/usuarios/{usuario_id}/postulaciones",
    response_model=CursorPageSchema[GetPostulacionSchema],
    summary="Listar mis postulaciones",
    description=(
        "Lista las postulaciones del usuario indicado con cursor. Solo se permite "
        "consultar las postulaciones de la propia identidad; oferta_id filtra opcionalmente."
    ),
    responses=error_responses(400, 401, 403, 404),
)
def get_postulaciones_by_usuario(
    usuario_id: Annotated[int, Path(..., description="Debe coincidir con el usuario autenticado.")],
    oferta_id: int | None = Query(default=None, ge=1, description="Filtro opcional por oferta."),
    limit: int = Query(default=20, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    page = PostulacionService(db).get_by_usuario(
        usuario_id,
        current_user.id,
        oferta_id=oferta_id,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetPostulacionSchema].model_validate(page)


@router.get(
    "/postulaciones/{postulacion_id}",
    response_model=GetPostulacionSchema,
    summary="Obtener postulación",
    description="Devuelve una postulación para su postulante o para OWNER/RECRUITER de la empresa.",
    responses=error_responses(401, 403, 404),
)
def get_postulacion(
    postulacion_id: Annotated[int, Path(..., description="Postulación que se consulta.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    postulacion: PostulacionResponseDTO = PostulacionService(db).get_by_id(
        postulacion_id,
        current_user.id,
    )
    return PostulacionMapper.to_response_schema(postulacion)


@router.patch(
    "/postulaciones/{postulacion_id}",
    response_model=GetPostulacionSchema,
    summary="Actualizar estado de postulación",
    description=(
        "Cambia el estado de una postulación. Solo OWNER o RECRUITER pueden hacerlo; "
        "las transiciones siguen el flujo nueva → vista → entrevista → contratado "
        "y permiten rechazo desde nueva, vista o entrevista. Contratar agrega "
        "COLLABORATOR si corresponde y despublica la oferta."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def update_postulacion(
    postulacion_id: Annotated[int, Path(..., description="Postulación cuyo estado se actualiza.")],
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
