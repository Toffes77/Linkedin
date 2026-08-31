from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.empresa_dto import (
    EmpresaResponseDTO,
)
from src.schemas.empresa_schema import (
    CreateEmpresaSchema,
    GetEmpresaSchema,
    UpdateEmpresaSchema,
)
from src.dtos.empresa_usuario_dto import (
    EmpresaUsuarioResponseDTO,
    MiEmpresaResponseDTO,
    MiembroEmpresaResponseDTO,
)
from src.mappers.empresa_mapper import EmpresaMapper
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper
from src.middlewares.auth_middleware import get_current_user
from src.schemas.empresa_usuario_schema import (
    CreateEmpresaUsuarioSchema,
    GetEmpresaUsuarioSchema,
    GetMiembroEmpresaSchema,
    GetMiEmpresaSchema,
    UpdateEmpresaUsuarioSchema,
)
from src.services.empresa_service import EmpresaService
from src.utils.image_storage import read_limited_upload
from src.services.empresa_usuario_service import EmpresaUsuarioService

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("", response_model=list[GetEmpresaSchema])
def search_empresas(
    q: str = Query(min_length=1, max_length=100, pattern=r".*\S.*"),
    db: Session = Depends(get_db),
):
    empresas = EmpresaService(db).search(q)
    return [EmpresaMapper.to_response_schema(empresa) for empresa in empresas]


@router.get("/me", response_model=list[GetMiEmpresaSchema])
def get_my_empresas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empresas: list[MiEmpresaResponseDTO] = EmpresaUsuarioService(
        db
    ).get_by_current_user(current_user.id)
    return [
        EmpresaUsuarioMapper.to_my_company_response_schema(empresa)
        for empresa in empresas
    ]


@router.post("", response_model=GetEmpresaSchema, status_code=status.HTTP_201_CREATED)
def create_empresa(
    payload: CreateEmpresaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = EmpresaMapper.to_create_dto(payload)
    empresa: EmpresaResponseDTO = EmpresaService(db).create(dto, current_user.id)
    return EmpresaMapper.to_response_schema(empresa)


@router.get("/{empresa_id}", response_model=GetEmpresaSchema)
def get_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa: EmpresaResponseDTO = EmpresaService(db).get_by_id(empresa_id)
    return EmpresaMapper.to_response_schema(empresa)


@router.put("/{empresa_id}", response_model=GetEmpresaSchema)
def update_empresa(
    empresa_id: int,
    payload: UpdateEmpresaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = EmpresaMapper.to_update_dto(payload)
    empresa: EmpresaResponseDTO = EmpresaService(db).update(
        empresa_id,
        dto,
        current_user.id,
    )
    return EmpresaMapper.to_response_schema(empresa)


@router.put("/{empresa_id}/foto-perfil", response_model=GetEmpresaSchema)
async def update_empresa_profile_photo(
    empresa_id: int,
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empresa: EmpresaResponseDTO = EmpresaService(db).update_profile_photo(
        empresa_id,
        current_user.id,
        foto.filename,
        await read_limited_upload(foto),
    )
    return EmpresaMapper.to_response_schema(empresa)


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
    return [EmpresaUsuarioMapper.to_response_schema(usuario) for usuario in usuarios]


@router.get("/{empresa_id}/miembros", response_model=list[GetMiembroEmpresaSchema])
def get_miembros_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
):
    miembros: list[MiembroEmpresaResponseDTO] = EmpresaUsuarioService(
        db
    ).get_public_members(empresa_id)
    return [
        EmpresaUsuarioMapper.to_member_response_schema(miembro)
        for miembro in miembros
    ]


@router.post("/{empresa_id}/usuarios", response_model=GetEmpresaUsuarioSchema, status_code=status.HTTP_201_CREATED)
def create_usuario_empresa(
    empresa_id: int,
    payload: CreateEmpresaUsuarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = EmpresaUsuarioMapper.to_create_dto(payload)
    usuario: EmpresaUsuarioResponseDTO = EmpresaUsuarioService(db).create(
        empresa_id,
        dto,
        current_user.id,
    )
    return EmpresaUsuarioMapper.to_response_schema(usuario)


@router.patch("/{empresa_id}/usuarios/{usuario_id}", response_model=GetEmpresaUsuarioSchema)
def update_usuario_empresa(
    empresa_id: int,
    usuario_id: int,
    payload: UpdateEmpresaUsuarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = EmpresaUsuarioMapper.to_update_dto(payload)
    usuario: EmpresaUsuarioResponseDTO = EmpresaUsuarioService(db).update(
        empresa_id,
        usuario_id,
        dto,
        current_user.id,
    )
    return EmpresaUsuarioMapper.to_response_schema(usuario)


@router.delete("/{empresa_id}/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usuario_empresa(
    empresa_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    EmpresaUsuarioService(db).delete(empresa_id, usuario_id, current_user.id)
