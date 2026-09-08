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

    model_config = ConfigDict(extra="forbid")

    oferta_id: int = Field(
        description="Oferta publicada a la que se postula."
    )


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
