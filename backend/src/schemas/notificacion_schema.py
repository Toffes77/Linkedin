from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

TipoNotificacion = Literal["POSTULACION_NUEVA", "POSTULACION_ESTADO"]


class NotificacionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    tipo: TipoNotificacion
    mensaje: str
    leida: bool
    fecha: datetime
    postulacion_id: int | None
    oferta_id: int | None


class NotificacionesNoLeidasSchema(BaseModel):
    cantidad: int
