from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.utils.text_validation import strip_non_blank


class CreateUsuarioSchema(BaseModel):
    """Datos públicos y credenciales necesarios para registrar un usuario."""

    email: EmailStr = Field(max_length=100, description="Email único de la cuenta.")
    password: str = Field(min_length=8, description="Contraseña de al menos 8 caracteres.")
    nombre: str = Field(min_length=1, max_length=100, description="Nombre visible del usuario.")
    headline: str = Field(min_length=1, max_length=200, description="Titular profesional visible en el perfil.")
    ciudad: str = Field(min_length=1, max_length=100, description="Ciudad válida del catálogo de ubicaciones.")

    @field_validator("nombre", "headline", "ciudad", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str):
        if len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return value


class LegacyUpdateUsuarioSchema(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, min_length=1, max_length=200)
    ciudad: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("nombre", "headline", "ciudad", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str | None):
        if value is not None and len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return value


class UpdateUsuarioSchema(BaseModel):
    """Campos editables del perfil propio; todos son opcionales."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, min_length=1, max_length=200)
    ciudad: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("nombre", "headline", "ciudad", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdatePasswordSchema(BaseModel):
    """Contraseña actual y nueva para cambiar las credenciales."""

    password_actual: str = Field(description="Contraseña vigente.")
    password_nueva: str = Field(min_length=8, description="Nueva contraseña de al menos 8 caracteres.")


class PasswordUpdateResponseSchema(BaseModel):
    """Confirmación del cambio de contraseña."""

    message: str = Field(description="Mensaje de confirmación.")


class ExperienciaUsuarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None


class GetUsuarioSchema(BaseModel):
    """Perfil público; nunca incluye la contraseña ni su hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str
    ciudad: str
    foto_perfil_url: str | None = None
    experiencias: list[ExperienciaUsuarioSchema]
