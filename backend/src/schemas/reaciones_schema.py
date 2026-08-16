from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateReaccionSchema(BaseModel):
    usuario_id: int
    publicacion_id: int
    tipo: Literal[
        "like",
        "celebrar",
        "apoyar",
        "interesante"
    ]


class UpdateReaccionSchema(BaseModel):
    tipo: Literal[
        "like",
        "celebrar",
        "apoyar",
        "interesante"
    ]


class GetReaccionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    publicacion_id: int
    tipo: str