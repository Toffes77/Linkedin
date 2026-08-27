from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CrearConversacionSchema(BaseModel):
    usuario_id: int = Field(gt=0)


class EnviarMensajeSchema(BaseModel):
    contenido: str = Field(max_length=2000)

    @field_validator("contenido")
    @classmethod
    def limpiar_contenido(cls, value: str) -> str:
        contenido = value.strip()
        if not contenido:
            raise ValueError("El mensaje no puede estar vacío.")
        return contenido


class CompartirPublicacionSchema(BaseModel):
    publicacion_id: int = Field(gt=0)


class ConversacionSchema(BaseModel):
    id: int
    usuario_id: int
    fecha_creacion: datetime


class PublicacionCompartidaSchema(BaseModel):
    id: int
    autor_id: int
    autor_nombre: str
    autor_headline: str
    autor_foto_perfil_url: str | None = None
    texto: str
    fecha: datetime


class MensajeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversacion_id: int
    autor_id: int
    contenido: str
    tipo: str
    publicacion_id: int | None = None
    publicacion: PublicacionCompartidaSchema | None = None
    fecha: datetime


class ContactoConversacionSchema(BaseModel):
    usuario_id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None
    conversacion_id: int | None = None
    ultimo_mensaje: str | None = None
    ultimo_mensaje_autor_id: int | None = None
    fecha_ultimo_mensaje: datetime | None = None
    no_leidos: int


class MensajesNoLeidosSchema(BaseModel):
    cantidad: int
