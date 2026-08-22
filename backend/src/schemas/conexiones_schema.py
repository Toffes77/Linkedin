from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.schemas.usuario_schema import GetUsuarioSchema


EstadoConexion = Literal["pendiente", "aceptada", "rechazada"]


class CreateConexionSchema(BaseModel):
    usuario_a: int
    usuario_b: int


class UpdateConexionSchema(BaseModel):
    estado: EstadoConexion


class GetConexionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: EstadoConexion


class ResumenRedResponseSchema(BaseModel):
    invitaciones_enviadas: int
    contactos: int
    siguiendo: int


class InvitacionRecibidaResponseSchema(BaseModel):
    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: EstadoConexion
    usuario: GetUsuarioSchema
