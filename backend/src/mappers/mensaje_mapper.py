from src.db.models.conversacion_model import Conversacion, Mensaje
from src.dtos.mensaje_dto import (
    ContactoConversacionDTO,
    ConversacionDTO,
    CrearConversacionDTO,
    EnviarMensajeDTO,
    MensajeDTO,
)
from src.schemas.mensaje_schema import (
    ContactoConversacionSchema,
    ConversacionSchema,
    CrearConversacionSchema,
    EnviarMensajeSchema,
    MensajeSchema,
)


class MensajeMapper:
    @staticmethod
    def to_create_conversation_dto(schema: CrearConversacionSchema) -> CrearConversacionDTO:
        return CrearConversacionDTO(**schema.model_dump())

    @staticmethod
    def to_send_message_dto(schema: EnviarMensajeSchema) -> EnviarMensajeDTO:
        return EnviarMensajeDTO(**schema.model_dump())

    @staticmethod
    def to_conversation_dto(
        conversacion: Conversacion,
        usuario_actual_id: int,
    ) -> ConversacionDTO:
        otro_usuario_id = (
            conversacion.usuario_mayor_id
            if conversacion.usuario_menor_id == usuario_actual_id
            else conversacion.usuario_menor_id
        )
        return ConversacionDTO(
            id=conversacion.id,
            usuario_id=otro_usuario_id,
            fecha_creacion=conversacion.fecha_creacion,
        )

    @staticmethod
    def to_message_dto(mensaje: Mensaje) -> MensajeDTO:
        return MensajeDTO.model_validate(mensaje)

    @staticmethod
    def to_conversation_schema(dto: ConversacionDTO) -> ConversacionSchema:
        return ConversacionSchema(**dto.model_dump())

    @staticmethod
    def to_message_schema(dto: MensajeDTO) -> MensajeSchema:
        return MensajeSchema(**dto.model_dump())

    @staticmethod
    def to_contact_schema(dto: ContactoConversacionDTO) -> ContactoConversacionSchema:
        return ContactoConversacionSchema(**dto.model_dump())

