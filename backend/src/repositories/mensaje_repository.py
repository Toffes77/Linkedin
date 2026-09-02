from sqlalchemy import case, func, or_, select, union_all
from sqlalchemy.orm import Session, joinedload

from src.db.models.conexiones_model import Conexion
from src.db.models.conversacion_model import Conversacion, ConversacionUsuario, Mensaje
from src.db.models.publicacion_model import Publicacion
from src.db.models.usuario_model import Usuario
from src.utils.datetime_utils import utc_now


class MensajeRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def ordenar_par(usuario_a: int, usuario_b: int) -> tuple[int, int]:
        return min(usuario_a, usuario_b), max(usuario_a, usuario_b)

    def get_by_pair(self, usuario_a: int, usuario_b: int) -> Conversacion | None:
        menor, mayor = self.ordenar_par(usuario_a, usuario_b)
        return (
            self.db.query(Conversacion)
            .filter(
                Conversacion.usuario_menor_id == menor,
                Conversacion.usuario_mayor_id == mayor,
            )
            .first()
        )

    def get_by_id(self, conversacion_id: int) -> Conversacion | None:
        return self.db.get(Conversacion, conversacion_id)

    def get_participation(
        self, conversacion_id: int, usuario_id: int
    ) -> ConversacionUsuario | None:
        return self.db.get(ConversacionUsuario, (conversacion_id, usuario_id))

    def create(self, usuario_a: int, usuario_b: int) -> Conversacion:
        menor, mayor = self.ordenar_par(usuario_a, usuario_b)
        ahora = utc_now()
        conversacion = Conversacion(
            usuario_menor_id=menor,
            usuario_mayor_id=mayor,
            fecha_creacion=ahora,
        )
        self.db.add(conversacion)
        self.db.flush()
        self.db.add_all(
            [
                ConversacionUsuario(
                    conversacion_id=conversacion.id,
                    usuario_id=menor,
                    ultima_lectura=ahora,
                ),
                ConversacionUsuario(
                    conversacion_id=conversacion.id,
                    usuario_id=mayor,
                    ultima_lectura=ahora,
                ),
            ]
        )
        self.db.commit()
        self.db.refresh(conversacion)
        return conversacion

    def list_contact_summaries(self, usuario_id: int):
        contactos = union_all(
            select(Conexion.usuario_b.label("usuario_id")).where(
                Conexion.usuario_a == usuario_id,
                Conexion.estado == "aceptada",
            ),
            select(Conexion.usuario_a.label("usuario_id")).where(
                Conexion.usuario_b == usuario_id,
                Conexion.estado == "aceptada",
            ),
        ).subquery("contactos_aceptados")

        ultimo_mensaje_id = (
            select(Mensaje.id)
            .where(Mensaje.conversacion_id == Conversacion.id)
            .order_by(Mensaje.fecha.desc(), Mensaje.id.desc())
            .limit(1)
            .correlate(Conversacion)
            .scalar_subquery()
        )
        no_leidos = (
            select(func.count(Mensaje.id))
            .where(
                Mensaje.conversacion_id == Conversacion.id,
                Mensaje.autor_id != usuario_id,
                Mensaje.leido_por_destinatario.is_(False),
            )
            .correlate(Conversacion)
            .scalar_subquery()
        )

        return (
            self.db.query(
                Usuario,
                Conversacion,
                Mensaje,
                no_leidos.label("no_leidos"),
            )
            .join(contactos, contactos.c.usuario_id == Usuario.id)
            .outerjoin(
                Conversacion,
                or_(
                    (
                        (Conversacion.usuario_menor_id == usuario_id)
                        & (Conversacion.usuario_mayor_id == Usuario.id)
                    ),
                    (
                        (Conversacion.usuario_mayor_id == usuario_id)
                        & (Conversacion.usuario_menor_id == Usuario.id)
                    ),
                ),
            )
            .outerjoin(Mensaje, Mensaje.id == ultimo_mensaje_id)
            .options(
                joinedload(Mensaje.publicacion).joinedload(Publicacion.autor)
            )
            .order_by(
                case((Mensaje.id.is_(None), 1), else_=0),
                Mensaje.fecha.desc(),
                Mensaje.id.desc(),
                func.lower(Usuario.nombre),
                Usuario.id,
            )
            .all()
        )

    def get_messages(
        self,
        conversacion_id: int,
        limit: int,
        offset: int,
    ) -> list[Mensaje]:
        mensajes = (
            self.db.query(Mensaje)
            .options(
                joinedload(Mensaje.publicacion).joinedload(Publicacion.autor)
            )
            .filter(Mensaje.conversacion_id == conversacion_id)
            .order_by(Mensaje.fecha.desc(), Mensaje.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return list(reversed(mensajes))

    def create_message(
        self,
        conversacion: Conversacion,
        autor_id: int,
        contenido: str,
    ) -> Mensaje:
        mensaje = Mensaje(
            conversacion_id=conversacion.id,
            autor_id=autor_id,
            contenido=contenido,
            tipo="TEXTO",
            fecha=utc_now(),
        )
        self.db.add(mensaje)
        self.db.flush()
        conversacion.fecha_ultimo_mensaje = mensaje.fecha or utc_now()
        self.db.commit()
        self.db.refresh(mensaje)
        return mensaje

    def create_shared_post_message(
        self,
        conversacion: Conversacion,
        autor_id: int,
        publicacion: Publicacion,
    ) -> Mensaje:
        mensaje = Mensaje(
            conversacion_id=conversacion.id,
            autor_id=autor_id,
            contenido="Publicación compartida",
            tipo="PUBLICACION",
            publicacion_id=publicacion.id,
            publicacion=publicacion,
            fecha=utc_now(),
        )
        self.db.add(mensaje)
        self.db.flush()
        conversacion.fecha_ultimo_mensaje = mensaje.fecha or utc_now()
        self.db.commit()
        self.db.refresh(mensaje)
        return mensaje

    def mark_as_read(
        self, participacion: ConversacionUsuario
    ) -> ConversacionUsuario:
        (
            self.db.query(Mensaje)
            .filter(
                Mensaje.conversacion_id == participacion.conversacion_id,
                Mensaje.autor_id != participacion.usuario_id,
                Mensaje.leido_por_destinatario.is_(False),
            )
            .update(
                {Mensaje.leido_por_destinatario: True},
                synchronize_session=False,
            )
        )
        participacion.ultima_lectura = utc_now()
        self.db.commit()
        self.db.refresh(participacion)
        return participacion

    def count_unread(self, usuario_id: int) -> int:
        return (
            self.db.query(func.count(Mensaje.id))
            .join(
                ConversacionUsuario,
                ConversacionUsuario.conversacion_id == Mensaje.conversacion_id,
            )
            .filter(
                ConversacionUsuario.usuario_id == usuario_id,
                Mensaje.autor_id != usuario_id,
                Mensaje.leido_por_destinatario.is_(False),
            )
            .scalar()
            or 0
        )
