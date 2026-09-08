from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.dtos.reacciones_dto import TipoReaccion
from src.utils.text_validation import strip_non_blank


class CreatePublicacionDTO(BaseModel):
    autor_id: int
    texto: str = Field(min_length=1, max_length=3000)

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class CreatePublicacionMultimediaDTO(BaseModel):
    autor_id: int
    texto: str = Field(default="", max_length=3000)

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return "" if value is None else str(value)


class UpdatePublicacionDTO(BaseModel):
    texto: str | None = Field(default=None, min_length=1, max_length=3000)

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdatePublicacionMultimediaDTO(BaseModel):
    texto: str = Field(default="", max_length=3000)

    @field_validator("texto", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return "" if value is None else str(value)


class DeletePublicacionDTO(BaseModel):
    id: int


class PublicacionMultimediaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ruta: str
    tipo: str
    orden: int


class MultimediaCreateDTO(BaseModel):
    ruta: str
    tipo: str
    orden: int


class PublicacionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_id: int
    texto: str
    fecha: datetime
    multimedia: list[PublicacionMultimediaDTO] = Field(default_factory=list)


class AutorPublicacionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None


class PublicacionCardDTO(PublicacionResponseDTO):
    autor: AutorPublicacionDTO
    reacciones: dict[TipoReaccion, int]
    mi_reaccion: TipoReaccion | None = None
    cantidad_comentarios: int
