from datetime import datetime

from pydantic import BaseModel, Field


class CrearComentarioDTO(BaseModel):
    contenido: str = Field(min_length=1, max_length=1000)


class GuardarComentarioDTO(BaseModel):
    publicacion_id: int
    usuario_id: int
    contenido: str = Field(min_length=1, max_length=1000)
    comentario_padre_id: int | None = None


class AutorComentarioDTO(BaseModel):
    id: int
    nombre: str
    headline: str | None = None
    foto_perfil_url: str | None = None


class ComentarioResponseDTO(BaseModel):
    id: int
    publicacion_id: int
    usuario_id: int
    contenido: str
    fecha: datetime
    comentario_padre_id: int | None = None
    autor: AutorComentarioDTO
    cantidad_respuestas: int = 0


class CantidadComentariosDTO(BaseModel):
    cantidad: int
