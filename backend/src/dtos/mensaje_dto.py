from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CrearConversacionDTO(BaseModel):
    usuario_id: int


class EnviarMensajeDTO(BaseModel):
    contenido: str = Field(min_length=1, max_length=2000)


class ConversacionDTO(BaseModel):
    id: int
    usuario_id: int
    fecha_creacion: datetime


class MensajeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversacion_id: int
    autor_id: int
    contenido: str
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

