from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SeguimientoResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seguidor_id: int
    seguido_id: int
    fecha: datetime


class EstadoSeguimientoResponseDTO(BaseModel):
    siguiendo: bool
