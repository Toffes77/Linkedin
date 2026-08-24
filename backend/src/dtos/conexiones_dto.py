from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.dtos.usuario_dto import UsuarioResponseDTO


EstadoConexion = Literal["pendiente", "aceptada", "rechazada"]
EstadoRelacionConexion = Literal[
    "SIN_CONEXION",
    "PENDIENTE_ENVIADA",
    "PENDIENTE_RECIBIDA",
    "CONECTADO",
    "RECHAZADA",
]


class CreateConexionDTO(BaseModel):
    usuario_a: int
    usuario_b: int


class UpdateConexionDTO(BaseModel):
    estado: EstadoConexion


class ConexionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: EstadoConexion


class EstadoConexionResponseDTO(BaseModel):
    estado: EstadoRelacionConexion
    usuario_a: int | None = None
    usuario_b: int | None = None


class ResumenRedResponseDTO(BaseModel):
    invitaciones_enviadas: int
    contactos: int
    siguiendo: int


class InvitacionRecibidaResponseDTO(BaseModel):
    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: EstadoConexion
    usuario: UsuarioResponseDTO
