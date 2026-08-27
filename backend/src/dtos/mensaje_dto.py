from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CrearConversacionDTO(BaseModel):
    usuario_id: int


class EnviarMensajeDTO(BaseModel):
    contenido: str = Field(min_length=1, max_length=2000)


class CompartirPublicacionDTO(BaseModel):
    publicacion_id: int


class ConversacionDTO(BaseModel):
    id: int
    usuario_id: int
    fecha_creacion: datetime


class PublicacionCompartidaDTO(BaseModel):
    id: int
    autor_id: int
    autor_nombre: str
    autor_headline: str
    autor_foto_perfil_url: str | None = None
    texto: str
    fecha: datetime


class MensajeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversacion_id: int
    autor_id: int
    contenido: str
    tipo: str = "TEXTO"
    publicacion_id: int | None = None
    publicacion: PublicacionCompartidaDTO | None = None
    fecha: datetime


class ContactoConversacionDTO(BaseModel):
    usuario_id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None
    conversacion_id: int | None = None
    ultimo_mensaje: str | None = None
    ultimo_mensaje_autor_id: int | None = None
    fecha_ultimo_mensaje: datetime | None = None
    no_leidos: int = 0
