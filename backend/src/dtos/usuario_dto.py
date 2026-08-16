from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUsuarioDTO(BaseModel):
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8)
    nombre: str = Field(min_length=1, max_length=100)
    headline: str = Field(min_length=1, max_length=200)
    ciudad: str = Field(min_length=1, max_length=100)


class UpdateUsuarioDTO(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, min_length=1, max_length=200)
    ciudad: str | None = Field(default=None, min_length=1, max_length=100)


class ExperienciaUsuarioDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None = None


class UsuarioResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str
    ciudad: str
    experiencias: list[ExperienciaUsuarioDTO]
