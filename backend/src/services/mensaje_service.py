from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.dtos.mensaje_dto import (
    CompartirPublicacionDTO,
    ContactoConversacionDTO,
    ConversacionDTO,
    CrearConversacionDTO,
    EnviarMensajeDTO,
    MensajeDTO,
)
from src.mappers.mensaje_mapper import MensajeMapper
from src.repositories.conexion_repository import ConexionRepository
from src.repositories.mensaje_repository import MensajeRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import BadRequestError, ForbiddenError, NotFoundError


class MensajeService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = MensajeRepository(db)
        self.conexion_repository = ConexionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.publicacion_repository = PublicacionRepository(db)

    def list_contacts(self, usuario_id: int) -> list[ContactoConversacionDTO]:
        return [
            ContactoConversacionDTO(
                usuario_id=usuario.id,
                nombre=usuario.nombre,
                headline=usuario.headline,
                foto_perfil_url=usuario.foto_perfil_url,
                conversacion_id=conversacion.id if conversacion else None,
                ultimo_mensaje=(
                    "Publicación compartida"
                    if ultimo_mensaje and ultimo_mensaje.tipo == "PUBLICACION"
                    else ultimo_mensaje.contenido if ultimo_mensaje else None
                ),
                ultimo_mensaje_autor_id=(
                    ultimo_mensaje.autor_id if ultimo_mensaje else None
                ),
                fecha_ultimo_mensaje=(
                    ultimo_mensaje.fecha if ultimo_mensaje else None
                ),
                no_leidos=int(no_leidos or 0),
            )
            for usuario, conversacion, ultimo_mensaje, no_leidos
            in self.repository.list_contact_summaries(usuario_id)
        ]

    def get_or_create(
        self,
        data: CrearConversacionDTO,
        usuario_id: int,
    ) -> ConversacionDTO:
        if data.usuario_id == usuario_id:
            raise BadRequestError("No puede iniciar una conversación consigo mismo.")
        if self.usuario_repository.get_by_id(data.usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")
        if not self.conexion_repository.has_accepted_connection(
            usuario_id,
            data.usuario_id,
        ):
            raise ForbiddenError(
                "Solo puede iniciar conversaciones con conexiones aceptadas."
            )

        conversacion = self.repository.get_by_pair(usuario_id, data.usuario_id)
        if conversacion is None:
            try:
                conversacion = self.repository.create(usuario_id, data.usuario_id)
            except IntegrityError:
                self.db.rollback()
                conversacion = self.repository.get_by_pair(usuario_id, data.usuario_id)
                if conversacion is None:
                    raise
        return MensajeMapper.to_conversation_dto(conversacion, usuario_id)

    def get_messages(
        self,
        conversacion_id: int,
        usuario_id: int,
        limit: int,
        offset: int,
    ) -> list[MensajeDTO]:
        self._require_participation(conversacion_id, usuario_id)
        return [
            MensajeMapper.to_message_dto(message)
            for message in self.repository.get_messages(
                conversacion_id,
                limit,
                offset,
            )
        ]

    def send_message(
        self,
        conversacion_id: int,
        data: EnviarMensajeDTO,
        usuario_id: int,
    ) -> MensajeDTO:
        conversacion, _ = self._require_participation(conversacion_id, usuario_id)
        contenido = data.contenido.strip()
        if not contenido:
            raise BadRequestError("El mensaje no puede estar vacío.")
        if len(contenido) > 2000:
            raise BadRequestError("El mensaje no puede superar los 2000 caracteres.")
        mensaje = self.repository.create_message(
            conversacion,
            autor_id=usuario_id,
            contenido=contenido,
        )
        return MensajeMapper.to_message_dto(mensaje)

    def share_post(
        self,
        conversacion_id: int,
        data: CompartirPublicacionDTO,
        usuario_id: int,
    ) -> MensajeDTO:
        conversacion, _ = self._require_participation(conversacion_id, usuario_id)
        publicacion = self.publicacion_repository.get_by_id(data.publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada.")
        mensaje = self.repository.create_shared_post_message(
            conversacion,
            autor_id=usuario_id,
            publicacion=publicacion,
        )
        return MensajeMapper.to_message_dto(mensaje)

    def mark_as_read(self, conversacion_id: int, usuario_id: int) -> None:
        _, participacion = self._require_participation(conversacion_id, usuario_id)
        self.repository.mark_as_read(participacion)

    def count_unread(self, usuario_id: int) -> int:
        return self.repository.count_unread(usuario_id)

    def _require_participation(self, conversacion_id: int, usuario_id: int):
        conversacion = self.repository.get_by_id(conversacion_id)
        if conversacion is None:
            raise NotFoundError("Conversación no encontrada.")
        participacion = self.repository.get_participation(conversacion_id, usuario_id)
        if participacion is None:
            raise ForbiddenError("No puede acceder a una conversación ajena.")
        return conversacion, participacion
