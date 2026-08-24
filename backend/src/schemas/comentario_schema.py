from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CrearComentarioSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contenido: str = Field(max_length=1000)

    @field_validator("contenido")
    @classmethod
    def limpiar_contenido(cls, value: str) -> str:
        contenido = value.strip()
        if not contenido:
            raise ValueError("El comentario no puede estar vacío.")
        return contenido


class AutorComentarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    headline: str | None = None
    foto_perfil_url: str | None = None


class GetComentarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publicacion_id: int
    usuario_id: int
    contenido: str
    fecha: datetime
    comentario_padre_id: int | None = None
    autor: AutorComentarioSchema
    cantidad_respuestas: int = 0
    respuestas: list[GetComentarioSchema] = Field(default_factory=list)


class CantidadComentariosSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cantidad: int
