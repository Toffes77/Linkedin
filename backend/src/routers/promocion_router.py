from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.mappers.promocion_mapper import PromocionMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.pagination_schema import CursorPageSchema
from src.schemas.promocion_schema import (
    CreatePromocionSchema,
    CreateSolicitudContratacionPromocionSchema,
    GetEmpresaContratanteSchema,
    GetPromocionSchema,
    GetSolicitudContratacionPromocionSchema,
)
from src.services.promocion_service import PromocionService
from src.utils.openapi import error_responses


router = APIRouter(tags=["tablón"])


@router.post("/promociones", response_model=GetPromocionSchema, status_code=status.HTTP_201_CREATED, summary="Crear promoción", description="Publica una promoción de servicios para el usuario autenticado.", responses=error_responses(401))
def create_promotion(payload: CreatePromocionSchema, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    promotion = PromocionService(db).create(PromocionMapper.to_create_dto(payload), current_user.id)
    return PromocionMapper.to_response_schema(promotion)


@router.get(
    "/promociones",
    response_model=CursorPageSchema[GetPromocionSchema],
    summary="Listar promociones del tablón",
    description=(
        "Lista promociones visibles para usuarios autenticados con paginación por cursor estable. "
        "No es un acceso anónimo desde Internet. "
        "Excluye la propia promoción y las promociones ya contratadas."
    ),
    responses=error_responses(400, 401),
)
def get_board_promotions(
    q: str | None = Query(default=None, description="Filtro opcional por título."),
    limit: int = Query(default=10, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = PromocionService(db).get_board_page(current_user.id, q=q, cursor=cursor, limit=limit)
    return CursorPageSchema[GetPromocionSchema].model_validate(result)


@router.get(
    "/promociones/mias",
    response_model=CursorPageSchema[GetPromocionSchema],
    summary="Listar mis promociones",
    description="Lista las promociones creadas por el usuario autenticado, sus propuestas pendientes y una contratación aceptada si existe.",
    responses=error_responses(400, 401),
)
def get_my_promotions(
    limit: int = Query(default=10, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(default=None, max_length=2048, description="Cursor opaco devuelto por la página anterior."),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    page = PromocionService(db).get_mine(current_user.id, cursor=cursor, limit=limit)
    return CursorPageSchema[GetPromocionSchema].model_validate(page)


@router.get(
    "/promociones/{promotion_id}/empresas-contratantes",
    response_model=list[GetEmpresaContratanteSchema],
    summary="Listar empresas que pueden contratar",
    description="Devuelve empresas donde el usuario es OWNER o RECRUITER, excluyendo membresías del candidato y propuestas vigentes.",
    responses=error_responses(401, 404, 409),
)
def get_hiring_companies(promotion_id: Annotated[int, Path(..., description="Promoción disponible que se quiere contratar.")], db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    companies = PromocionService(db).get_hiring_companies(promotion_id, current_user.id)
    return [PromocionMapper.company_to_schema(item) for item in companies]


@router.post(
    "/promociones/{promotion_id}/solicitudes-contratacion",
    response_model=GetSolicitudContratacionPromocionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear propuesta de contratación",
    description="Crea una propuesta PENDIENTE desde una empresa donde el usuario es OWNER o RECRUITER. Una promoción contratada no admite propuestas nuevas.",
    responses=error_responses(401, 403, 404, 409),
)
def create_hiring_request(promotion_id: Annotated[int, Path(..., description="Promoción a la que se dirige la propuesta.")], payload: CreateSolicitudContratacionPromocionSchema, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    request = PromocionService(db).create_hiring_request(promotion_id, PromocionMapper.to_hiring_request_dto(payload), current_user.id)
    return PromocionMapper.hiring_request_to_schema(request)


@router.post(
    "/solicitudes-contratacion-promocion/{request_id}/aceptar",
    response_model=GetSolicitudContratacionPromocionSchema,
    summary="Aceptar propuesta de contratación",
    description="Acepta una propuesta PENDIENTE del autor, crea la membresía COLLABORATOR si falta y cierra automáticamente las demás propuestas pendientes. Solo una propuesta puede quedar ACEPTADA por promoción.",
    responses=error_responses(401, 403, 404, 409),
)
def accept_hiring_request(request_id: Annotated[int, Path(..., description="Propuesta de contratación que se acepta.")], db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    request = PromocionService(db).accept_hiring_request(request_id, current_user.id)
    return PromocionMapper.hiring_request_to_schema(request)


@router.post(
    "/solicitudes-contratacion-promocion/{request_id}/rechazar",
    response_model=GetSolicitudContratacionPromocionSchema,
    summary="Rechazar propuesta de contratación",
    description="Rechaza una propuesta PENDIENTE dirigida al autor de la promoción.",
    responses=error_responses(401, 403, 404, 409),
)
def reject_hiring_request(request_id: Annotated[int, Path(..., description="Propuesta de contratación que se rechaza.")], db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    request = PromocionService(db).reject_hiring_request(request_id, current_user.id)
    return PromocionMapper.hiring_request_to_schema(request)
