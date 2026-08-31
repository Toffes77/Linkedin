from typing import Literal

from pydantic import BaseModel, ConfigDict


TipoReaccion = Literal["like", "celebrar", "apoyar", "interesante"]


class CreateReaccionSchema(BaseModel):
    publicacion_id: int
    tipo: TipoReaccion


class UpdateReaccionSchema(BaseModel):
    tipo: TipoReaccion


class GetReaccionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    publicacion_id: int
    tipo: TipoReaccion
