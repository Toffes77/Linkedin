from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from src.utils.text_validation import strip_non_blank


class CreateEmpresaSchema(BaseModel):
    """Datos de una empresa nueva; el creador queda como OWNER."""

    nombre: str = Field(min_length=1, max_length=100, description="Nombre público de la empresa.")
    industria: str | None = Field(default=None, max_length=100, description="Industria o sector.")
    sitio_web: HttpUrl | None = Field(default=None, max_length=255, description="Sitio web público válido.")

    @field_validator("nombre", "industria", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdateEmpresaSchema(BaseModel):
    """Campos editables por un OWNER; los campos omitidos conservan su valor."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100, description="Nuevo nombre público.")
    industria: str | None = Field(default=None, max_length=100, description="Nueva industria o null.")
    sitio_web: HttpUrl | None = Field(default=None, max_length=255, description="Nuevo sitio web o null.")

    @field_validator("nombre", "industria", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class GetEmpresaSchema(BaseModel):
    """Datos públicos de una empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    industria: str | None = None
    sitio_web: str | None = None
    foto_perfil_url: str | None = None
