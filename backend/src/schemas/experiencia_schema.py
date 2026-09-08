from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.utils.experience_dates import validar_fechas_experiencia
from src.utils.text_validation import strip_non_blank


class CreateExperienciaSchema(BaseModel):
    """Experiencia laboral que se agregará al usuario autenticado."""

    empresa_id: int = Field(description="Empresa asociada.")
    puesto: str = Field(min_length=1, max_length=100, description="Puesto o rol desempeñado.")
    desde: date = Field(
        description="Fecha de inicio, inclusive; no puede ser posterior a la fecha actual."
    )
    hasta: date | None = Field(
        default=None,
        description=(
            "Fecha de finalización; null significa experiencia vigente. No puede "
            "ser posterior a la fecha actual ni anterior a desde."
        ),
    )

    @field_validator("puesto", mode="before")
    @classmethod
    def normalizar_puesto(cls, value):
        return strip_non_blank(value)

    @model_validator(mode="after")
    def validar_fechas(self):
        validar_fechas_experiencia(self.desde, self.hasta)
        return self


class UpdateExperienciaSchema(BaseModel):
    """Campos opcionales para editar una experiencia propia."""

    empresa_id: int | None = Field(
        default=None,
        description="Nueva empresa asociada; si se envía, debe existir.",
    )
    puesto: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Nuevo puesto o rol desempeñado.",
    )
    desde: date | None = Field(
        default=None,
        description="Nueva fecha de inicio, inclusive; no puede ser posterior a la fecha actual.",
    )
    hasta: date | None = Field(
        default=None,
        description=(
            "Nueva fecha de finalización; null deja la experiencia vigente. No puede "
            "ser posterior a la fecha actual ni anterior a desde."
        ),
    )

    @field_validator("puesto", mode="before")
    @classmethod
    def normalizar_puesto(cls, value):
        return strip_non_blank(value)

    @model_validator(mode="after")
    def validar_fechas(self):
        validar_fechas_experiencia(self.desde, self.hasta)
        return self


class DeleteExperienciaSchema(BaseModel):
    """Identificador histórico de una experiencia a eliminar."""

    id: int


class GetExperienciaSchema(BaseModel):
    """Experiencia laboral devuelta dentro de un perfil o al crearla."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None

