from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, Query, UploadFile, status
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
from src.schemas.pagination_schema import CursorPageSchema
from src.schemas.usuario_schema import GetUsuarioSchema
from src.services.empresa_service import EmpresaService
from src.utils.image_storage import read_limited_upload
from src.services.empresa_usuario_service import EmpresaUsuarioService
from src.utils.openapi import error_responses

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get(
    "",
    response_model=list[GetEmpresaSchema],
    summary="Buscar empresas",
    description="Busca empresas por nombre parcial. No requiere autenticación.",
)
def search_empresas(
    q: str = Query(
        min_length=1,
        max_length=100,
        pattern=r".*\S.*",
        description="Nombre o texto parcial, de 1 a 100 caracteres.",
    ),
    db: Session = Depends(get_db),
):
    empresas = EmpresaService(db).search(q)
    return [EmpresaMapper.to_response_schema(empresa) for empresa in empresas]


@router.get(
    "/me",
    response_model=list[GetMiEmpresaSchema],
    summary="Listar mis empresas",
    description="Devuelve todas las empresas a las que pertenece el usuario autenticado y su rol.",
    responses=error_responses(401),
)
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


@router.post(
    "",
    response_model=GetEmpresaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear empresa",
    description="Crea una empresa y asigna automáticamente el rol OWNER al usuario autenticado.",
    responses=error_responses(401),
)
def create_empresa(
    payload: CreateEmpresaSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = EmpresaMapper.to_create_dto(payload)
    empresa: EmpresaResponseDTO = EmpresaService(db).create(dto, current_user.id)
    return EmpresaMapper.to_response_schema(empresa)


@router.get(
    "/batch",
    response_model=list[GetEmpresaSchema],
    summary="Obtener empresas por lote",
    description="Devuelve las empresas existentes cuyos IDs se envían repetidos en la query ids.",
    responses=error_responses(400),
)
def get_empresas_batch(
    ids: list[int] = Query(
        min_length=1,
        max_length=50,
        description="Lista de 1 a 50 IDs; se eliminan duplicados conservando el orden.",
    ),
    db: Session = Depends(get_db),
):
    empresas = EmpresaService(db).get_by_ids(ids)
    return [EmpresaMapper.to_response_schema(empresa) for empresa in empresas]


@router.get(
    "/{empresa_id}",
    response_model=GetEmpresaSchema,
    summary="Obtener empresa",
    description="Devuelve los datos públicos de una empresa.",
    responses=error_responses(404),
)
def get_empresa(
    empresa_id: Annotated[int, Path(..., description="Identificador de la empresa.")],
    db: Session = Depends(get_db),
):
    empresa: EmpresaResponseDTO = EmpresaService(db).get_by_id(empresa_id)
    return EmpresaMapper.to_response_schema(empresa)


@router.put(
    "/{empresa_id}",
    response_model=GetEmpresaSchema,
    summary="Actualizar empresa",
    description="Actualiza datos públicos de una empresa. Solo OWNER puede hacerlo.",
    responses=error_responses(401, 403, 404),
)
def update_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa que se desea actualizar.")],
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


@router.put(
    "/{empresa_id}/foto-perfil",
    response_model=GetEmpresaSchema,
    summary="Actualizar logo de empresa",
    description="Reemplaza el logo de una empresa. Solo OWNER puede hacerlo; acepta imágenes de hasta 5 MiB.",
    responses=error_responses(400, 401, 403, 404),
)
async def update_empresa_profile_photo(
    empresa_id: Annotated[int, Path(..., description="Empresa cuyo logo se actualiza.")],
    foto: UploadFile = File(
        ...,
        description="Imagen JPG, JPEG, PNG o WEBP válida de hasta 5 MiB.",
    ),
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


@router.get(
    "/{empresa_id}/usuarios",
    response_model=list[GetEmpresaUsuarioSchema],
    summary="Listar miembros administrables",
    description="Lista las relaciones de miembros y roles. Solo OWNER puede consultar este listado administrativo.",
    responses=error_responses(401, 403, 404),
)
def get_usuarios_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa cuyos miembros se consultan.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    usuarios: list[EmpresaUsuarioResponseDTO] = EmpresaUsuarioService(db).get_by_empresa(
        empresa_id,
        current_user.id,
    )
    return [EmpresaUsuarioMapper.to_response_schema(usuario) for usuario in usuarios]


@router.get(
    "/{empresa_id}/usuarios/candidatos",
    response_model=CursorPageSchema[GetUsuarioSchema],
    summary="Buscar candidatos a miembro",
    description=(
        "Busca usuarios por nombre que todavía no pertenecen a la empresa. "
        "Solo OWNER puede usar esta búsqueda y la respuesta usa cursor."
    ),
    responses=error_responses(400, 401, 403, 404),
)
def search_candidatos_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa para la que se buscan candidatos.")],
    q: str = Query(
        min_length=2,
        max_length=100,
        pattern=r".*\S.*",
        description="Nombre parcial de al menos 2 caracteres.",
    ),
    limit: int = Query(default=10, ge=1, le=20, description="Cantidad por página (1 a 20)."),
    cursor: str | None = Query(
        default=None,
        max_length=2048,
        description="Cursor opaco devuelto por la página anterior.",
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    page = EmpresaUsuarioService(db).search_candidates(
        empresa_id,
        current_user.id,
        q,
        cursor=cursor,
        limit=limit,
    )
    return CursorPageSchema[GetUsuarioSchema].model_validate(page)


@router.get(
    "/{empresa_id}/miembros",
    response_model=list[GetMiembroEmpresaSchema],
    summary="Listar miembros públicos",
    description="Devuelve los miembros visibles de una empresa; no requiere autenticación.",
    responses=error_responses(404),
)
def get_miembros_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa cuyos miembros públicos se consultan.")],
    db: Session = Depends(get_db),
):
    miembros: list[MiembroEmpresaResponseDTO] = EmpresaUsuarioService(
        db
    ).get_public_members(empresa_id)
    return [
        EmpresaUsuarioMapper.to_member_response_schema(miembro)
        for miembro in miembros
    ]


@router.post(
    "/{empresa_id}/usuarios",
    response_model=GetEmpresaUsuarioSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar miembro a empresa",
    description="Agrega un usuario a una empresa con un rol. Solo OWNER puede administrar miembros.",
    responses=error_responses(401, 403, 404, 409),
)
def create_usuario_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa a la que se incorpora el usuario.")],
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


@router.patch(
    "/{empresa_id}/usuarios/{usuario_id}",
    response_model=GetEmpresaUsuarioSchema,
    summary="Cambiar rol de miembro",
    description=(
        "Cambia el rol de un miembro. Solo OWNER puede hacerlo y la empresa "
        "debe conservar al menos un OWNER."
    ),
    responses=error_responses(401, 403, 404, 409),
)
def update_usuario_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa del miembro.")],
    usuario_id: Annotated[int, Path(..., description="Usuario cuyo rol se actualiza.")],
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


@router.delete(
    "/{empresa_id}/usuarios/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar miembro de empresa",
    description="Elimina una relación de membresía. Solo OWNER puede hacerlo y no se puede eliminar el último OWNER.",
    responses=error_responses(401, 403, 404, 409),
)
def delete_usuario_empresa(
    empresa_id: Annotated[int, Path(..., description="Empresa del miembro.")],
    usuario_id: Annotated[int, Path(..., description="Usuario que se retira de la empresa.")],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    EmpresaUsuarioService(db).delete(empresa_id, usuario_id, current_user.id)
