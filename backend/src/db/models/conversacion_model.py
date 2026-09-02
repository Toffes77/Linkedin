from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.connection import Base


class Conversacion(Base):
    __tablename__ = "conversacion"

    id = Column(Integer, primary_key=True)
    usuario_menor_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    usuario_mayor_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    fecha_creacion = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    fecha_ultimo_mensaje = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "usuario_menor_id < usuario_mayor_id",
            name="conversacion_par_ordenado_check",
        ),
        UniqueConstraint(
            "usuario_menor_id",
            "usuario_mayor_id",
            name="uq_conversacion_par_privado",
        ),
        Index("idx_conversacion_ultimo_mensaje", "fecha_ultimo_mensaje"),
    )

    participantes = relationship(
        "ConversacionUsuario",
        back_populates="conversacion",
        cascade="all, delete-orphan",
    )
    mensajes = relationship(
        "Mensaje",
        back_populates="conversacion",
        cascade="all, delete-orphan",
    )


class ConversacionUsuario(Base):
    __tablename__ = "conversacion_usuario"

    conversacion_id = Column(
        Integer,
        ForeignKey("conversacion.id", ondelete="CASCADE"),
        primary_key=True,
    )
    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ultima_lectura = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_conversacion_usuario_usuario", "usuario_id", "conversacion_id"),
    )

    conversacion = relationship("Conversacion", back_populates="participantes")
    usuario = relationship("Usuario")


class Mensaje(Base):
    __tablename__ = "mensaje"

    id = Column(Integer, primary_key=True)
    conversacion_id = Column(
        Integer,
        ForeignKey("conversacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    autor_id = Column(Integer, nullable=False)
    contenido = Column(String(2000), nullable=False)
    tipo = Column(String(20), nullable=False, server_default="TEXTO")
    publicacion_id = Column(
        Integer,
        ForeignKey("publicacion.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    leido_por_destinatario = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="FALSE",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["conversacion_id", "autor_id"],
            [
                "conversacion_usuario.conversacion_id",
                "conversacion_usuario.usuario_id",
            ],
            ondelete="CASCADE",
            name="fk_mensaje_autor_participante",
        ),
        CheckConstraint(
            "length(contenido) BETWEEN 1 AND 2000 "
            "AND contenido ~ '[^[:space:]]'",
            name="mensaje_contenido_check",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "tipo IN ('TEXTO', 'PUBLICACION')",
            name="mensaje_tipo_check",
        ),
        CheckConstraint(
            "tipo = 'PUBLICACION' OR publicacion_id IS NULL",
            name="mensaje_publicacion_tipo_check",
        ),
        Index(
            "idx_mensaje_conversacion_fecha",
            "conversacion_id",
            "fecha",
            "id",
        ),
        Index(
            "idx_mensaje_conversacion_no_leido",
            "conversacion_id",
            "autor_id",
            postgresql_where=(leido_por_destinatario.is_(False)),
        ),
    )

    conversacion = relationship("Conversacion", back_populates="mensajes")
    publicacion = relationship("Publicacion")
