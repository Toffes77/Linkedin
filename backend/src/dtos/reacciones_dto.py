from typing import Literal

from pydantic import BaseModel, ConfigDict


TipoReaccion = Literal["like", "celebrar", "apoyar", "interesante"]


class CreateReaccionDTO(BaseModel):
    usuario_id: int
    publicacion_id: int
    tipo: TipoReaccion


class UpdateReaccionDTO(BaseModel):
    tipo: TipoReaccion


class ReaccionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    publicacion_id: int
    tipo: TipoReaccion
