from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    EstadoConexionResponseDTO,
)
from src.mappers.conexion_mapper import ConexionMapper
from src.schemas.conexiones_schema import (
    CreateConexionSchema,
    EstadoConexionResponseSchema,
    GetConexionSchema,
    UpdateConexionSchema,
    ResumenRedResponseSchema,
    InvitacionRecibidaResponseSchema,
)
from src.middlewares.auth_middleware import get_current_user
from src.services.conexion_service import ConexionService

router = APIRouter(prefix="/conexiones", tags=["conexiones"])


@router.get("/resumen", response_model=ResumenRedResponseSchema)
def get_resumen_red(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    resumen = ConexionService(db).get_resumen_red(current_user.id)
    return ConexionMapper.to_resumen_response_schema(resumen)


@router.get(
    "/invitaciones-recibidas",
    response_model=list[InvitacionRecibidaResponseSchema],
)
def get_invitaciones_recibidas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    invitations = ConexionService(db).get_invitaciones_recibidas(current_user.id)
    return [
        ConexionMapper.to_invitacion_response_schema(invitation)
        for invitation in invitations
    ]


@router.get(
    "/estado/{usuario_id}",
    response_model=EstadoConexionResponseSchema,
)
def get_estado_conexion(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estado: EstadoConexionResponseDTO = ConexionService(db).get_estado(
        current_user.id,
        usuario_id,
    )
    return ConexionMapper.to_estado_response_schema(estado)


@router.post("", response_model=GetConexionSchema, status_code=status.HTTP_201_CREATED)
def create_conexion(
    payload: CreateConexionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ConexionMapper.to_create_dto(payload)
    conexion: ConexionResponseDTO = ConexionService(db).create(dto, current_user.id)
    return ConexionMapper.to_response_schema(conexion)


@router.patch("/{usuario_a}/{usuario_b}", response_model=GetConexionSchema)
def update_conexion(
    usuario_a: int,
    usuario_b: int,
    payload: UpdateConexionSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    dto = ConexionMapper.to_update_dto(payload)
    conexion: ConexionResponseDTO = ConexionService(db).update(
        usuario_a,
        usuario_b,
        dto,
        current_user.id,
    )
    return ConexionMapper.to_response_schema(conexion)
