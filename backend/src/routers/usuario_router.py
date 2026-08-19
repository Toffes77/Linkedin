from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.usuario_dto import CreateUsuarioDTO, UsuarioResponseDTO
from src.schemas.usuario_schema import CreateUsuarioSchema, GetUsuarioSchema
from src.services.usuario_service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=GetUsuarioSchema, status_code=status.HTTP_201_CREATED)
def create_usuario(
    payload: CreateUsuarioSchema,
    db: Session = Depends(get_db),
):
    dto = CreateUsuarioDTO(**payload.model_dump())
    usuario: UsuarioResponseDTO = UsuarioService(db).create(dto)
    return GetUsuarioSchema.model_validate(usuario)


@router.get("/{usuario_id}", response_model=GetUsuarioSchema)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario: UsuarioResponseDTO = UsuarioService(db).get_by_id(usuario_id)
    return GetUsuarioSchema.model_validate(usuario)
