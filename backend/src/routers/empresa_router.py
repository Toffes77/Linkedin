from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.empresa_dto import (
    CreateEmpresaDTO,
    EmpresaResponseDTO,
    UpdateEmpresaDTO,
)
from src.schemas.empresa_schema import (
    CreateEmpresaSchema,
    GetEmpresaSchema,
    UpdateEmpresaSchema,
)
from src.services.empresa_service import EmpresaService

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.post("", response_model=GetEmpresaSchema, status_code=status.HTTP_201_CREATED)
def create_empresa(
    payload: CreateEmpresaSchema,
    db: Session = Depends(get_db),
):
    dto = CreateEmpresaDTO(**payload.model_dump())
    empresa: EmpresaResponseDTO = EmpresaService(db).create(dto)
    return GetEmpresaSchema.model_validate(empresa)


@router.get("/{empresa_id}", response_model=GetEmpresaSchema)
def get_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa: EmpresaResponseDTO = EmpresaService(db).get_by_id(empresa_id)
    return GetEmpresaSchema.model_validate(empresa)


@router.put("/{empresa_id}", response_model=GetEmpresaSchema)
def update_empresa(
    empresa_id: int,
    payload: UpdateEmpresaSchema,
    db: Session = Depends(get_db),
):
    dto = UpdateEmpresaDTO(**payload.model_dump(exclude_unset=True))
    empresa: EmpresaResponseDTO = EmpresaService(db).update(empresa_id, dto)
    return GetEmpresaSchema.model_validate(empresa)
