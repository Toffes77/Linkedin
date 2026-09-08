from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.utils.text_validation import strip_non_blank


class CreateExperienciaSchema(BaseModel):
    """Experiencia laboral que se agregará al usuario autenticado."""

    empresa_id: int = Field(description="Empresa asociada.")
    puesto: str = Field(min_length=1, max_length=100, description="Puesto o rol desempeñado.")
    desde: date = Field(description="Fecha de inicio, inclusive.")
    hasta: date | None = Field(default=None, description="Fecha de finalización; null significa experiencia vigente.")

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
    """Schema interno para actualización; actualmente no está expuesto por un router."""

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
    """Schema interno para eliminación; actualmente no está expuesto por un router."""

    id: int


class GetExperienciaSchema(BaseModel):
    """Experiencia laboral devuelta dentro de un perfil o al crearla."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None

