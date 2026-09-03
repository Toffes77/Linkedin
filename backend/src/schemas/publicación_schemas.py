from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas.reaciones_schema import TipoReaccion
from src.utils.text_validation import strip_non_blank


class CreatePublicacionSchema(BaseModel):
    texto: str = Field(min_length=1, max_length=3000)

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdatePublicacionSchema(BaseModel):
    texto: str | None = Field(
        default=None,
        min_length=1,
        max_length=3000
    )

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class DeletePublicacionSchema(BaseModel):
    id: int


class GetPublicacionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_id: int
    texto: str
    fecha: datetime


class GetAutorPublicacionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None


class GetPublicacionCardSchema(GetPublicacionSchema):
    autor: GetAutorPublicacionSchema
    reacciones: dict[TipoReaccion, int]
    mi_reaccion: TipoReaccion | None = None
    cantidad_comentarios: int
