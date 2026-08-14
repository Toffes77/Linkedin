from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime


class CreateUsuarioSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str = Field(min_length=1, max_length=100)
    headline: str = Field(min_length=1, max_length=200)
    ciudad: str = Field(min_length=1, max_length=100)


class UpdateUsuarioSchema(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, min_length=1, max_length=200)
    ciudad: str | None = Field(default=None, min_length=1, max_length=100)


class DeleteUsuarioSchema(BaseModel):
    id: int


class ExperienciaUsuarioSchema(BaseModel):
    id: int
    empresa_id: int
    puesto: str
    desde: date
    hasta: date | None


class GetUsuarioSchema(BaseModel):
    id: int
    nombre: str
    headline: str
    ciudad: str
    experiencias: list[ExperienciaUsuarioSchema]