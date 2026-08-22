from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


EstadoPostulacion = Literal[
    "nueva",
    "vista",
    "entrevista",
    "contratado",
    "rechazada",
]


class CreatePostulacionSchema(BaseModel):
    oferta_id: int
    usuario_id: int


class UpdatePostulacionSchema(BaseModel):
    estado: EstadoPostulacion


class GetPostulacionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    oferta_id: int
    oferta_titulo: str
    usuario_id: int
    fecha: datetime
    estado: EstadoPostulacion
