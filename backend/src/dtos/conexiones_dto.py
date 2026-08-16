from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


EstadoConexion = Literal["pendiente", "aceptada", "rechazada"]


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
