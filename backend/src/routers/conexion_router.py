from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    CreateConexionDTO,
    UpdateConexionDTO,
)
from src.schemas.conexiones_schema import (
    CreateConexionSchema,
    GetConexionSchema,
    UpdateConexionSchema,
)
from src.middlewares.auth_middleware import get_current_user
from src.services.conexion_service import ConexionService

router = APIRouter(prefix="/conexiones", tags=["conexiones"])


@router.post("", response_model=GetConexionSchema, status_code=status.HTTP_201_CREATED)
def create_conexion(
    payload: CreateConexionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = CreateConexionDTO(**payload.model_dump())
    conexion: ConexionResponseDTO = ConexionService(db).create(dto, current_user.id)
    return GetConexionSchema.model_validate(conexion)


@router.patch("/{usuario_a}/{usuario_b}", response_model=GetConexionSchema)
def update_conexion(
    usuario_a: int,
    usuario_b: int,
    payload: UpdateConexionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = UpdateConexionDTO(**payload.model_dump())
    conexion: ConexionResponseDTO = ConexionService(db).update(
        usuario_a,
        usuario_b,
        dto,
        current_user.id,
    )
    return GetConexionSchema.model_validate(conexion)
