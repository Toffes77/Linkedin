from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TipoReaccion = Literal["like", "celebrar", "apoyar", "interesante"]


class CreateReaccionSchema(BaseModel):
    """Reacción del usuario autenticado sobre una publicación."""

    publicacion_id: int = Field(description="Publicación que recibe la reacción.")
    tipo: TipoReaccion = Field(description="Tipo: like, celebrar, apoyar o interesante.")


class UpdateReaccionSchema(BaseModel):
    """Nuevo tipo para la reacción propia existente."""

    tipo: TipoReaccion = Field(description="Tipo: like, celebrar, apoyar o interesante.")


class GetReaccionSchema(BaseModel):
    """Reacción persistida."""

    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    publicacion_id: int
    tipo: TipoReaccion
