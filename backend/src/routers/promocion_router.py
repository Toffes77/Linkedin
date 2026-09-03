from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.promocion_dto import PromocionResponseDTO
from src.mappers.promocion_mapper import PromocionMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.promocion_schema import (
    CreatePromocionSchema,
    CreateSolicitudContratacionPromocionSchema,
    GetEmpresaContratanteSchema,
    GetPromocionSchema,
    GetPromocionesPaginadasSchema,
    GetSolicitudContratacionPromocionSchema,
)
from src.schemas.pagination_schema import CursorPageSchema
from src.services.promocion_service import PromocionService

router = APIRouter(tags=["tablón"])


@router.post(
    "/promociones",
    response_model=GetPromocionSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_promotion(
    payload: CreatePromocionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    promotion = PromocionService(db).create(
        PromocionMapper.to_create_dto(payload),
        current_user.id,
    )
    return PromocionMapper.to_response_schema(promotion)


@router.get("/promociones", response_model=GetPromocionesPaginadasSchema)
def get_public_promotions(
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = PromocionService(db).get_public_page(
        current_user.id,
        q=q,
        page=page,
        page_size=page_size,
    )
    return PromocionMapper.to_page_schema(result)


@router.get(
    "/promociones/mias",
    response_model=CursorPageSchema[GetPromocionSchema],
)
def get_my_promotions(
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=2048),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    page = PromocionService(db).get_mine(
        current_user.id,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetPromocionSchema].model_validate(page)


@router.get(
    "/promociones/{promotion_id}/empresas-contratantes",
    response_model=list[GetEmpresaContratanteSchema],
)
def get_hiring_companies(
    promotion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    companies = PromocionService(db).get_hiring_companies(
        promotion_id,
        current_user.id,
    )
    return [PromocionMapper.company_to_schema(item) for item in companies]


@router.post(
    "/promociones/{promotion_id}/solicitudes-contratacion",
    response_model=GetSolicitudContratacionPromocionSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_hiring_request(
    promotion_id: int,
    payload: CreateSolicitudContratacionPromocionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    request = PromocionService(db).create_hiring_request(
        promotion_id,
        PromocionMapper.to_hiring_request_dto(payload),
        current_user.id,
    )
    return PromocionMapper.hiring_request_to_schema(request)


@router.post(
    "/solicitudes-contratacion-promocion/{request_id}/aceptar",
    response_model=GetSolicitudContratacionPromocionSchema,
)
def accept_hiring_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    request = PromocionService(db).accept_hiring_request(
        request_id,
        current_user.id,
    )
    return PromocionMapper.hiring_request_to_schema(request)
