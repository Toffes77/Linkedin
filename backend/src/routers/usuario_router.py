from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.usuario_dto import UsuarioResponseDTO
from src.mappers.usuario_mapper import UsuarioMapper
from src.schemas.usuario_schema import CreateUsuarioSchema, GetUsuarioSchema
from src.services.conexion_service import ConexionService
from src.services.usuario_service import UsuarioService

router = APIRouter(tags=["usuarios"])


@router.post("/usuarios", response_model=GetUsuarioSchema, status_code=status.HTTP_201_CREATED)
def create_usuario(
    payload: CreateUsuarioSchema,
    db: Session = Depends(get_db),
):
    dto = UsuarioMapper.to_create_dto(payload)
    usuario: UsuarioResponseDTO = UsuarioService(db).create(dto)
    return UsuarioMapper.to_response_schema(usuario)


@router.get("/usuarios/{usuario_id}", response_model=GetUsuarioSchema)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario: UsuarioResponseDTO = UsuarioService(db).get_by_id(usuario_id)
    return UsuarioMapper.to_response_schema(usuario)


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
