from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateConexionSchema(BaseModel):
    usuario_a: int
    usuario_b: int


class UpdateConexionSchema(BaseModel):
    estado: Literal[
        "pendiente",
        "aceptada",
        "rechazada"
    ]


class GetConexionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_a: int
    usuario_b: int
    fecha: datetime
    estado: str