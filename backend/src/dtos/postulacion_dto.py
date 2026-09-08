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


class CreatePostulacionDTO(BaseModel):
    oferta_id: int
    usuario_id: int


class UpdatePostulacionDTO(BaseModel):
    estado: EstadoPostulacion


class PostulantePostulacionDTO(BaseModel):
    id: int
    nombre: str
    foto_perfil_url: str | None = None


class PostulacionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    oferta_id: int
    oferta_titulo: str
    usuario_id: int
    postulante: PostulantePostulacionDTO
    fecha: datetime
    estado: EstadoPostulacion
