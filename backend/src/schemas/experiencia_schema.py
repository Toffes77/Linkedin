from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.utils.text_validation import strip_non_blank


class CreateExperienciaSchema(BaseModel):
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
        if self.hasta is not None and self.desde > self.hasta:
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de finalización"
            )
        return self


class UpdateExperienciaSchema(BaseModel):
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
        if self.desde is not None and self.hasta is not None:
            if self.desde > self.hasta:
                raise ValueError(
                    "La fecha de inicio no puede ser posterior a la fecha de finalización"
                )
        return self


class DeleteExperienciaSchema(BaseModel):
    id: int


class GetExperienciaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None

