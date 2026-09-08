from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
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
from src.utils.openapi import error_responses

router = APIRouter(tags=["tablón"])


@router.post(
    "/promociones",
    response_model=GetPromocionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear promoción",
    description="Publica una promoción de servicios para el usuario autenticado.",
    responses=error_responses(401),
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


@router.get(
    "/promociones",
    response_model=GetPromocionesPaginadasSchema,
    summary="Listar promociones públicas",
    description=(
        "Lista promociones disponibles para contratación con paginación tradicional. "
        "Requiere autenticación para excluir la propia promoción y calcular disponibilidad."
    ),
    responses=error_responses(401),
)
def get_public_promotions(
    q: str | None = Query(default=None, description="Filtro opcional por título."),
    page: int = Query(default=1, ge=1, description="Número de página, comenzando en 1."),
    page_size: int = Query(default=10, ge=1, le=50, description="Cantidad por página (1 a 50)."),
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
    summary="Listar mis promociones",
    description="Lista las promociones creadas por el usuario autenticado con sus propuestas y cursor.",
    responses=error_responses(400, 401),
)
def get_my_promotions(
    limit: int = Query(default=10, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
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
    summary="Listar empresas que pueden contratar",
    description=(
        "Devuelve empresas del usuario autenticado con OWNER o RECRUITER que pueden "
        "enviar una propuesta para una promoción disponible."
    ),
    responses=error_responses(401, 404, 409),
)
def get_hiring_companies(
    promotion_id: Annotated[int, Path(..., description="Promoción disponible que se quiere contratar.")],
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
    summary="Crear propuesta de contratación",
    description=(
        "Crea una propuesta desde una empresa donde el usuario es OWNER o RECRUITER. "
        "La promoción debe estar disponible y el candidato no debe ser miembro de la empresa."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def create_hiring_request(
    promotion_id: Annotated[int, Path(..., description="Promoción a la que se dirige la propuesta.")],
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
    summary="Aceptar propuesta de contratación",
    description=(
        "Acepta una propuesta dirigida al autor de la promoción. Crea la membresía "
        "COLLABORATOR si todavía no existe y marca la propuesta como ACEPTADA."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def accept_hiring_request(
    request_id: Annotated[int, Path(..., description="Propuesta de contratación que se acepta.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    request = PromocionService(db).accept_hiring_request(
        request_id,
        current_user.id,
    )
    return PromocionMapper.hiring_request_to_schema(request)
