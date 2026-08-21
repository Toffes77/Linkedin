from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import PasswordUpdateResponseDTO, UsuarioResponseDTO
from src.mappers.usuario_mapper import UsuarioMapper
from src.schemas.usuario_schema import (
    CreateUsuarioSchema,
    GetUsuarioSchema,
    PasswordUpdateResponseSchema,
    UpdatePasswordSchema,
    UpdateUsuarioSchema,
)
from src.services.conexion_service import ConexionService
from src.services.usuario_service import UsuarioService
from src.middlewares.auth_middleware import get_current_user

router = APIRouter(tags=["usuarios"])


@router.post("/usuarios", response_model=GetUsuarioSchema, status_code=status.HTTP_201_CREATED)
def create_usuario(
    payload: CreateUsuarioSchema,
    db: Session = Depends(get_db),
):
    dto = UsuarioMapper.to_create_dto(payload)
    usuario: UsuarioResponseDTO = UsuarioService(db).create(dto)
    return UsuarioMapper.to_response_schema(usuario)


@router.get("/usuarios/me", response_model=GetUsuarioSchema)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuario: UsuarioResponseDTO = UsuarioService(db).get_by_id(current_user.id)
    return UsuarioMapper.to_response_schema(usuario)


@router.get("/usuarios/{usuario_id}", response_model=GetUsuarioSchema)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario: UsuarioResponseDTO = UsuarioService(db).get_by_id(usuario_id)
    return UsuarioMapper.to_response_schema(usuario)


@router.put("/usuarios/me", response_model=GetUsuarioSchema)
def update_my_profile(
    payload: UpdateUsuarioSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UsuarioMapper.to_update_dto(payload)
    usuario: UsuarioResponseDTO = UsuarioService(db).update_profile(
        current_user.id,
        dto,
    )
    return UsuarioMapper.to_response_schema(usuario)


@router.put("/usuarios/me/foto-perfil", response_model=GetUsuarioSchema)
async def update_my_profile_photo(
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuario: UsuarioResponseDTO = UsuarioService(db).update_profile_photo(
        current_user.id,
        foto.filename,
        await foto.read(),
    )
    return UsuarioMapper.to_response_schema(usuario)


@router.put(
    "/usuarios/me/password",
    response_model=PasswordUpdateResponseSchema,
)
def update_my_password(
    payload: UpdatePasswordSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UsuarioMapper.to_update_password_dto(payload)
    response: PasswordUpdateResponseDTO = UsuarioService(db).update_password(
        current_user.id,
        dto,
    )
    return UsuarioMapper.to_password_update_response_schema(response)


@router.get("/usuarios/{usuario_id}/sugerencias", response_model=list[GetUsuarioSchema])
def get_sugerencias(usuario_id: int, db: Session = Depends(get_db)):
    usuarios = ConexionService(db).get_second_degree_suggestions(usuario_id)
    return [UsuarioMapper.to_response_schema(usuario) for usuario in usuarios]


@router.get("/buscar/usuarios", response_model=list[GetUsuarioSchema])
def buscar_usuarios(
    q: str = Query(min_length=1, max_length=200, pattern=r".*\S.*"),
    ciudad: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r".*\S.*",
    ),
    db: Session = Depends(get_db),
):
    usuarios = UsuarioService(db).search(q, ciudad)
    return [UsuarioMapper.to_response_schema(usuario) for usuario in usuarios]
