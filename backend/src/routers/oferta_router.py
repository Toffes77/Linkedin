from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.oferta_dto import (
    CreateOfertaDTO,
    OfertaEstadisticasDTO,
    OfertaResponseDTO,
    UpdateOfertaDTO,
)
from src.schemas.oferta_schema import (
    CreateOfertaSchema,
    GetOfertaSchema,
    GetOfertaEstadisticasSchema,
    UpdateOfertaSchema,
)
from src.middlewares.auth_middleware import get_current_user
from src.services.oferta_service import OfertaService

router = APIRouter(tags=["ofertas"])


@router.post(
    "/ofertas",
    response_model=GetOfertaSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_oferta(
    payload: CreateOfertaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreateOfertaDTO(**payload.model_dump())
    oferta: OfertaResponseDTO = OfertaService(db).create(dto, current_user.id)
    return GetOfertaSchema.model_validate(oferta)


@router.get("/ofertas/publicadas", response_model=list[GetOfertaSchema])
def get_ofertas_publicadas(db: Session = Depends(get_db)):
    ofertas: list[OfertaResponseDTO] = OfertaService(db).get_publicadas()
    return [GetOfertaSchema.model_validate(oferta) for oferta in ofertas]


@router.get("/empresas/{empresa_id}/ofertas", response_model=list[GetOfertaSchema])
def get_ofertas_by_empresa(empresa_id: int, db: Session = Depends(get_db)):
    ofertas: list[OfertaResponseDTO] = OfertaService(db).get_by_empresa(empresa_id)
    return [GetOfertaSchema.model_validate(oferta) for oferta in ofertas]


@router.get("/ofertas/{oferta_id}", response_model=GetOfertaSchema)
def get_oferta(oferta_id: int, db: Session = Depends(get_db)):
    oferta: OfertaResponseDTO = OfertaService(db).get_by_id(oferta_id)
    return GetOfertaSchema.model_validate(oferta)


@router.put("/ofertas/{oferta_id}", response_model=GetOfertaSchema)
def update_oferta(
    oferta_id: int,
    payload: UpdateOfertaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdateOfertaDTO(**payload.model_dump(exclude_unset=True))
    oferta: OfertaResponseDTO = OfertaService(db).update(
        oferta_id,
        dto,
        current_user.id,
    )
    return GetOfertaSchema.model_validate(oferta)


@router.get(
    "/ofertas/{oferta_id}/estadisticas",
    response_model=GetOfertaEstadisticasSchema,
)
def get_estadisticas_oferta(
    oferta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estadisticas: OfertaEstadisticasDTO = OfertaService(db).get_estadisticas(
        oferta_id,
        current_user.id,
    )
    return GetOfertaEstadisticasSchema.model_validate(estadisticas)
