from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from src.utils.text_validation import strip_non_blank


class CreateEmpresaSchema(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: HttpUrl | None = Field(default=None, max_length=255)

    @field_validator("nombre", "industria", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdateEmpresaSchema(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: HttpUrl | None = Field(default=None, max_length=255)

    @field_validator("nombre", "industria", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class GetEmpresaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    industria: str | None = None
    sitio_web: str | None = None
    foto_perfil_url: str | None = None
