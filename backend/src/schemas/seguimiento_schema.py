from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SeguimientoResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seguidor_id: int
    seguido_id: int
    fecha: datetime


class EstadoSeguimientoResponseSchema(BaseModel):
    siguiendo: bool
