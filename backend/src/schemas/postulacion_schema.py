from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EstadoPostulacion = Literal[
    "nueva",
    "vista",
    "entrevista",
    "contratado",
    "rechazada",
]


class CreatePostulacionSchema(BaseModel):
    """Postulación del usuario autenticado a una oferta publicada."""

    oferta_id: int = Field(description="Oferta publicada a la que se postula.")
    usuario_id: int = Field(description="Usuario postulante; debe coincidir con la identidad autenticada.")


class UpdatePostulacionSchema(BaseModel):
    """Nuevo estado administrado por OWNER o RECRUITER."""

    estado: EstadoPostulacion = Field(description="Estado destino de la postulación.")


class GetPostulacionSchema(BaseModel):
    """Postulación con oferta, usuario, fecha y estado actual."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    oferta_id: int
    oferta_titulo: str
    usuario_id: int
    fecha: datetime
    estado: EstadoPostulacion
