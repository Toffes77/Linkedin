from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CreateUsuarioSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str = Field(min_length=1, max_length=100)
    headline: str = Field(min_length=1, max_length=200)
    ciudad: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str):
        if len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return value


class UpdateUsuarioSchema(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, min_length=1, max_length=200)
    ciudad: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str | None):
        if value is not None and len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return value


class ExperienciaUsuarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None


class GetUsuarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str
    ciudad: str
    experiencias: list[ExperienciaUsuarioSchema]