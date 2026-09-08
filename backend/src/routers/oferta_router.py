from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.oferta_dto import (
    OfertaEstadisticasDTO,
    OfertaResponseDTO,
)
from src.mappers.oferta_mapper import OfertaMapper
from src.schemas.oferta_schema import (
    CreateOfertaSchema,
    GetOfertaSchema,
    GetOfertaEstadisticasSchema,
    UpdateOfertaSchema,
)
from src.schemas.pagination_schema import CursorPageSchema
from src.middlewares.auth_middleware import get_current_user, get_optional_current_user
from src.services.oferta_service import OfertaService
from src.utils.openapi import error_responses

router = APIRouter(tags=["ofertas"])


@router.post(
    "/ofertas",
    response_model=GetOfertaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear oferta",
    description="Crea una oferta para una empresa. Solo OWNER o RECRUITER pueden gestionarla.",
    responses=error_responses(401, 403, 404),
)
def create_oferta(
    payload: CreateOfertaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = OfertaMapper.to_create_dto(payload)
    oferta: OfertaResponseDTO = OfertaService(db).create(dto, current_user.id)
    return OfertaMapper.to_response_schema(oferta)


@router.get(
    "/ofertas/publicadas",
    response_model=CursorPageSchema[GetOfertaSchema],
    summary="Listar ofertas publicadas",
    description="Lista ofertas visibles públicamente, opcionalmente filtradas por título, con cursor.",
    responses=error_responses(400),
)
def get_ofertas_publicadas(
    q: str | None = Query(default=None, description="Filtro opcional por título parcial."),
    limit: int = Query(default=20, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
    db: Session = Depends(get_db),
):
    page = OfertaService(db).get_publicadas(q, cursor=cursor, limit=limit)
    return CursorPageSchema[GetOfertaSchema].model_validate(page)


@router.get(
    "/empresas/{empresa_id}/ofertas",
    response_model=CursorPageSchema[GetOfertaSchema],
    summary="Listar ofertas de una empresa",
    description=(
        "Devuelve ofertas de una empresa con cursor. Público solo para ofertas "
        "publicadas; OWNER y RECRUITER también pueden ver borradores propios."
    ),
    responses=error_responses(400, 401, 404),
)
def get_ofertas_by_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa cuyas ofertas se consultan.")],
    limit: int = Query(default=20, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
    db: Session = Depends(get_db),
    current_user: Usuario | None = Depends(get_optional_current_user),
):
    page = OfertaService(db).get_by_empresa(
        empresa_id,
        current_user.id if current_user else None,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetOfertaSchema].model_validate(page)


@router.get(
    "/ofertas/{oferta_id}",
    response_model=GetOfertaSchema,
    summary="Obtener oferta",
    description="Devuelve una oferta publicada; una oferta no publicada solo es visible para OWNER o RECRUITER de su empresa.",
    responses=error_responses(401, 404),
)
def get_oferta(
    oferta_id: Annotated[int, Path(..., description="Oferta que se consulta.")],
    db: Session = Depends(get_db),
    current_user: Usuario | None = Depends(get_optional_current_user),
):
    oferta: OfertaResponseDTO = OfertaService(db).get_by_id(
        oferta_id,
        current_user.id if current_user else None,
    )
    return OfertaMapper.to_response_schema(oferta)


@router.put(
    "/ofertas/{oferta_id}",
    response_model=GetOfertaSchema,
    summary="Actualizar oferta",
    description="Actualiza título, descripción o publicación de una oferta. Solo OWNER o RECRUITER pueden hacerlo.",
    responses=error_responses(401, 403, 404),
)
def update_oferta(
    oferta_id: Annotated[int, Path(..., description="Oferta que se actualiza.")],
    payload: UpdateOfertaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = OfertaMapper.to_update_dto(payload)
    oferta: OfertaResponseDTO = OfertaService(db).update(
        oferta_id,
        dto,
        current_user.id,
    )
    return OfertaMapper.to_response_schema(oferta)


@router.get(
    "/ofertas/{oferta_id}/estadisticas",
    response_model=GetOfertaEstadisticasSchema,
    summary="Consultar estadísticas de oferta",
    description=(
        "Devuelve el total y el desglose por estado de las postulaciones. "
        "Solo OWNER o RECRUITER de la empresa pueden consultarlo."
    ),
    responses=error_responses(401, 403, 404),
)
def get_estadisticas_oferta(
    oferta_id: Annotated[int, Path(..., description="Oferta cuyas postulaciones se resumen.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estadisticas: OfertaEstadisticasDTO = OfertaService(db).get_estadisticas(
        oferta_id,
        current_user.id,
    )
    return OfertaMapper.to_statistics_schema(estadisticas)
