from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SeguimientoResponseSchema(BaseModel):
    """Relación de seguimiento creada entre dos usuarios."""

    model_config = ConfigDict(from_attributes=True)

    seguidor_id: int
    seguido_id: int
    fecha: datetime


class EstadoSeguimientoResponseSchema(BaseModel):
    """Indica si el usuario autenticado sigue al usuario consultado."""

    siguiendo: bool
