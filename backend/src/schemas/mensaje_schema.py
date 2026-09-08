from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CrearConversacionSchema(BaseModel):
    """Usuario con el que se quiere abrir o recuperar una conversación."""

    usuario_id: int = Field(gt=0, description="Otro usuario; debe existir una conexión aceptada.")


class EnviarMensajeSchema(BaseModel):
    """Contenido de un mensaje de texto privado."""

    contenido: str = Field(max_length=2000, description="Texto no vacío de hasta 2000 caracteres.")

    @field_validator("contenido")
    @classmethod
    def limpiar_contenido(cls, value: str) -> str:
        contenido = value.strip()
        if not contenido:
            raise ValueError("El mensaje no puede estar vacío.")
        return contenido


class CompartirPublicacionSchema(BaseModel):
    """Referencia a una publicación que se comparte en una conversación."""

    publicacion_id: int = Field(gt=0, description="Publicación existente que se mostrará en el mensaje.")


class ConversacionSchema(BaseModel):
    """Conversación uno a uno recuperada o creada."""

    id: int
    usuario_id: int
    fecha_creacion: datetime


class PublicacionCompartidaSchema(BaseModel):
    """Vista embebida de una publicación compartida en un mensaje."""

    id: int
    autor_id: int
    autor_nombre: str
    autor_headline: str
    autor_foto_perfil_url: str | None = None
    texto: str
    fecha: datetime


class MensajeSchema(BaseModel):
    """Mensaje de texto o de tipo PUBLICACION."""

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
    """Resumen de un contacto y su conversación, si existe."""

    usuario_id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None
    conversacion_id: int | None = None
    ultimo_mensaje: str | None = None
    ultimo_mensaje_autor_id: int | None = None
    fecha_ultimo_mensaje: datetime | None = None
    no_leidos: int
    conectados: bool


class MensajesNoLeidosSchema(BaseModel):
    """Cantidad de mensajes no leídos del usuario autenticado."""

    cantidad: int
