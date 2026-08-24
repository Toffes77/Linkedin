from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

TipoNotificacion = Literal[
    "POSTULACION_NUEVA",
    "POSTULACION_ESTADO",
    "NUEVO_SEGUIDOR",
    "NUEVA_INVITACION_CONEXION",
    "CONEXION_ACEPTADA",
]


class CreateNotificacionDTO(BaseModel):
    usuario_id: int
    tipo: TipoNotificacion
    mensaje: str
    postulacion_id: int | None = None
    oferta_id: int | None = None
    usuario_origen_id: int | None = None


class NotificacionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    tipo: TipoNotificacion
    mensaje: str
    leida: bool
    fecha: datetime
    postulacion_id: int | None = None
    oferta_id: int | None = None
    usuario_origen_id: int | None = None
