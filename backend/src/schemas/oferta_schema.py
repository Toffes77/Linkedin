from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateOfertaSchema(BaseModel):
    empresa_id: int
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    publicada: bool = False


class UpdateOfertaSchema(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1)
    publicada: bool | None = None


class GetOfertaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    titulo: str
    descripcion: str
    publicada: bool
    fecha_publicacion: datetime | None = None