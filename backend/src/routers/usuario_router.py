from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
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
from src.schemas.pagination_schema import CursorPageSchema
from src.services.conexion_service import ConexionService
from src.services.usuario_service import UsuarioService
from src.utils.image_storage import read_limited_upload
from src.middlewares.auth_middleware import get_current_user
from src.utils.openapi import error_responses

router = APIRouter(tags=["usuarios"])


@router.post(
    "/usuarios",
    response_model=GetUsuarioSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario",
    description=(
        "Crea una cuenta y normaliza el email y la ciudad. La contraseña se "
        "almacena hasheada y nunca se devuelve en la respuesta. "
        "acepta_terminos debe ser true para validar el registro; ese valor "
        "no se persiste."
    ),
    responses=error_responses(400, 409),
)
def create_usuario(
    payload: CreateUsuarioSchema,
    db: Session = Depends(get_db),
):
    dto = UsuarioMapper.to_create_dto(payload)
    usuario: UsuarioResponseDTO = UsuarioService(db).create(dto)
    return UsuarioMapper.to_response_schema(usuario)


@router.get(
    "/usuarios/me",
    response_model=GetUsuarioSchema,
    summary="Obtener mi perfil",
    description="Devuelve el perfil completo del usuario autenticado, incluyendo sus experiencias.",
    responses=error_responses(401),
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuario: UsuarioResponseDTO = UsuarioService(db).get_by_id(current_user.id)
    return UsuarioMapper.to_response_schema(usuario)


@router.get(
    "/usuarios/{usuario_id}",
    response_model=GetUsuarioSchema,
    summary="Obtener perfil público",
    description="Devuelve el perfil público y las experiencias de un usuario existente.",
    responses=error_responses(404),
)
def get_usuario(
    usuario_id: Annotated[int, Path(..., description="Identificador del usuario.")],
    db: Session = Depends(get_db),
):
    usuario: UsuarioResponseDTO = UsuarioService(db).get_by_id(usuario_id)
    return UsuarioMapper.to_response_schema(usuario)


@router.put(
    "/usuarios/me",
    response_model=GetUsuarioSchema,
    summary="Actualizar mi perfil",
    description=(
        "Actualiza nombre, titular profesional y/o ciudad del usuario autenticado. "
        "Los campos omitidos conservan su valor."
    ),
    responses=error_responses(400, 401, 404),
)
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


@router.put(
    "/usuarios/me/foto-perfil",
    response_model=GetUsuarioSchema,
    summary="Actualizar foto de perfil",
    description="Reemplaza la foto de perfil del usuario autenticado por una imagen validada de hasta 5 MiB.",
    responses=error_responses(400, 401, 404),
)
async def update_my_profile_photo(
    foto: UploadFile = File(
        ...,
        description="Imagen JPG, JPEG, PNG o WEBP válida de hasta 5 MiB.",
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuario: UsuarioResponseDTO = UsuarioService(db).update_profile_photo(
        current_user.id,
        foto.filename,
        await read_limited_upload(foto),
    )
    return UsuarioMapper.to_response_schema(usuario)


@router.put(
    "/usuarios/me/password",
    response_model=PasswordUpdateResponseSchema,
    summary="Cambiar contraseña",
    description=(
        "Cambia la contraseña del usuario autenticado luego de verificar la actual. "
        "La nueva contraseña debe tener al menos 8 caracteres y ser diferente."
    ),
    responses=error_responses(400, 401),
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


@router.get(
    "/usuarios/{usuario_id}/sugerencias",
    response_model=list[GetUsuarioSchema],
    summary="Obtener sugerencias de contactos",
    description="Devuelve usuarios sugeridos de segundo grado para el usuario indicado.",
    responses=error_responses(404),
)
def get_sugerencias(
    usuario_id: Annotated[int, Path(..., description="Usuario para el que se calculan sugerencias.")],
    db: Session = Depends(get_db),
):
    usuarios = ConexionService(db).get_second_degree_suggestions(usuario_id)
    return [UsuarioMapper.to_response_schema(usuario) for usuario in usuarios]


@router.get(
    "/buscar/usuarios",
    response_model=CursorPageSchema[GetUsuarioSchema],
    summary="Buscar usuarios",
    description=(
        "Busca usuarios por nombre o texto relacionado y opcionalmente por ciudad. "
        "La respuesta usa cursor; reutilizá next_cursor sin modificarlo."
    ),
    responses=error_responses(400),
)
def buscar_usuarios(
    q: str = Query(
        min_length=1,
        max_length=200,
        pattern=r".*\S.*",
        description="Texto de búsqueda, de 1 a 200 caracteres.",
    ),
    ciudad: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r".*\S.*",
        description="Filtro opcional por ciudad.",
    ),
    limit: int = Query(default=20, ge=1, le=50, description="Cantidad por página (1 a 50)."),
    cursor: str | None = Query(
        default=None,
        max_length=2048,
        description="Cursor opaco devuelto por la página anterior.",
    ),
    db: Session = Depends(get_db),
):
    page = UsuarioService(db).search(
        q,
        ciudad,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetUsuarioSchema].model_validate(page)
