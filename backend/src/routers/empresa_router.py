from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
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
from src.dtos.empresa_usuario_dto import (
    CreateEmpresaUsuarioDTO,
    EmpresaUsuarioResponseDTO,
    UpdateEmpresaUsuarioDTO,
)
from src.middlewares.auth_middleware import get_current_user
from src.schemas.empresa_usuario_schema import (
    CreateEmpresaUsuarioSchema,
    GetEmpresaUsuarioSchema,
    UpdateEmpresaUsuarioSchema,
)
from src.services.empresa_service import EmpresaService
from src.services.empresa_usuario_service import EmpresaUsuarioService

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.post("", response_model=GetEmpresaSchema, status_code=status.HTTP_201_CREATED)
def create_empresa(
    payload: CreateEmpresaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreateEmpresaDTO(**payload.model_dump())
    empresa: EmpresaResponseDTO = EmpresaService(db).create(dto, current_user.id)
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
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdateEmpresaDTO(**payload.model_dump(exclude_unset=True))
    empresa: EmpresaResponseDTO = EmpresaService(db).update(
        empresa_id,
        dto,
        current_user.id,
    )
    return GetEmpresaSchema.model_validate(empresa)


@router.get("/{empresa_id}/usuarios", response_model=list[GetEmpresaUsuarioSchema])
def get_usuarios_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuarios: list[EmpresaUsuarioResponseDTO] = EmpresaUsuarioService(db).get_by_empresa(
        empresa_id,
        current_user.id,
    )
    return [GetEmpresaUsuarioSchema.model_validate(usuario) for usuario in usuarios]


@router.post("/{empresa_id}/usuarios", response_model=GetEmpresaUsuarioSchema, status_code=status.HTTP_201_CREATED)
def create_usuario_empresa(
    empresa_id: int,
    payload: CreateEmpresaUsuarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreateEmpresaUsuarioDTO(**payload.model_dump())
    usuario: EmpresaUsuarioResponseDTO = EmpresaUsuarioService(db).create(
        empresa_id,
        dto,
        current_user.id,
    )
    return GetEmpresaUsuarioSchema.model_validate(usuario)


@router.patch("/{empresa_id}/usuarios/{usuario_id}", response_model=GetEmpresaUsuarioSchema)
def update_usuario_empresa(
    empresa_id: int,
    usuario_id: int,
    payload: UpdateEmpresaUsuarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdateEmpresaUsuarioDTO(**payload.model_dump())
    usuario: EmpresaUsuarioResponseDTO = EmpresaUsuarioService(db).update(
        empresa_id,
        usuario_id,
        dto,
        current_user.id,
    )
    return GetEmpresaUsuarioSchema.model_validate(usuario)


@router.delete("/{empresa_id}/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usuario_empresa(
    empresa_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    EmpresaUsuarioService(db).delete(empresa_id, usuario_id, current_user.id)
