from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.utils.text_validation import strip_non_blank


class CreateOfertaDTO(BaseModel):
    empresa_id: int
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1)
    publicada: bool = False
    fecha_publicacion: datetime | None = None

    @field_validator("titulo", "descripcion", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdateOfertaDTO(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1)
    publicada: bool | None = None

    @field_validator("titulo", "descripcion", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class OfertaResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    titulo: str
    descripcion: str
    publicada: bool
    fecha_publicacion: datetime | None = None


class OfertaEstadisticasDTO(BaseModel):
    oferta_id: int
    total_postulaciones: int
    postulaciones_por_estado: dict[str, int]
    dias_desde_publicacion: int | None = None
