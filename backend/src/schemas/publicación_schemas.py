from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas.reaciones_schema import TipoReaccion
from src.utils.text_validation import strip_non_blank


class CreatePublicacionSchema(BaseModel):
    """Publicación de texto creada por el usuario autenticado."""

    texto: str = Field(min_length=1, max_length=3000, description="Contenido de la publicación; máximo 3000 caracteres.")

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdatePublicacionSchema(BaseModel):
    """Texto nuevo de una publicación propia."""

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
    """Schema histórico no utilizado por los endpoints actuales."""

    id: int


class GetPublicacionMultimediaSchema(BaseModel):
    """Archivo multimedia asociado a una publicación."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ruta: str
    tipo: str
    orden: int


class GetPublicacionSchema(BaseModel):
    """Publicación con sus datos básicos y multimedia ordenada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_id: int
    texto: str
    fecha: datetime
    multimedia: list[GetPublicacionMultimediaSchema] = Field(default_factory=list)


class GetAutorPublicacionSchema(BaseModel):
    """Datos públicos del autor mostrados en una tarjeta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None


class GetPublicacionCardSchema(GetPublicacionSchema):
    """Publicación enriquecida para feed, perfiles y detalle."""

    autor: GetAutorPublicacionSchema
    reacciones: dict[TipoReaccion, int]
    mi_reaccion: TipoReaccion | None = None
    cantidad_comentarios: int
