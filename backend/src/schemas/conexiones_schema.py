from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.usuario_schema import GetUsuarioSchema


EstadoConexion = Literal["pendiente", "aceptada", "rechazada"]
EstadoRelacionConexion = Literal[
    "SIN_CONEXION",
    "PENDIENTE_ENVIADA",
    "PENDIENTE_RECIBIDA",
    "CONECTADO",
    "RECHAZADA",
]


class CreateConexionSchema(BaseModel):
    """Solicitud de conexión iniciada por usuario_a."""

    usuario_a: int = Field(description="Usuario autenticado que envía la solicitud.")
    usuario_b: int = Field(description="Usuario destinatario de la solicitud.")


class UpdateConexionSchema(BaseModel):
    """Respuesta del destinatario a una solicitud pendiente."""

    estado: EstadoConexion = Field(description="Solo se aceptan los valores aceptada o rechazada al responder.")


class GetConexionSchema(BaseModel):
    """Conexión con sus usuarios, fecha y estado persistido."""

    model_config = ConfigDict(from_attributes=True)

    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: EstadoConexion


class EstadoConexionResponseSchema(BaseModel):
    """Estado de la relación entre el usuario autenticado y otro usuario."""

    estado: EstadoRelacionConexion
    usuario_a: int | None = None
    usuario_b: int | None = None


class ResumenRedResponseSchema(BaseModel):
    """Contadores de la red profesional del usuario autenticado."""

    invitaciones_enviadas: int
    contactos: int
    siguiendo: int


class InvitacionRecibidaResponseSchema(BaseModel):
    """Invitación pendiente recibida, incluyendo el perfil del remitente."""

    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: EstadoConexion
    usuario: GetUsuarioSchema
