from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.utils.experience_dates import validar_fechas_experiencia
from src.utils.text_validation import strip_non_blank


class CreateExperienciaDTO(BaseModel):
    usuario_id: int
    empresa_id: int
    puesto: str = Field(min_length=1, max_length=100)
    desde: date
    hasta: date | None = None

    @field_validator("puesto", mode="before")
    @classmethod
    def normalizar_puesto(cls, value):
        return strip_non_blank(value)

    @model_validator(mode="after")
    def validar_fechas(self):
        validar_fechas_experiencia(self.desde, self.hasta)
        return self


class UpdateExperienciaDTO(BaseModel):
    empresa_id: int | None = None
    puesto: str | None = Field(default=None, min_length=1, max_length=100)
    desde: date | None = None
    hasta: date | None = None

    @field_validator("puesto", mode="before")
    @classmethod
    def normalizar_puesto(cls, value):
        return strip_non_blank(value)

    @model_validator(mode="after")
    def validar_fechas(self):
        validar_fechas_experiencia(self.desde, self.hasta)
        return self


class DeleteExperienciaDTO(BaseModel):
    id: int


class ExperienciaResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None
