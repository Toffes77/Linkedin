from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, CheckConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.connection import Base


class Conexion(Base):
    __tablename__ = "conexiones"

    usuario_a = Column(
        Integer,
        ForeignKey("usuario.id"),
        primary_key=True,
        nullable=False
    )

    usuario_b = Column(
        Integer,
        ForeignKey("usuario.id"),
        primary_key=True,
        nullable=False
    )

    fecha = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    estado = Column(
        String(20),
        default="pendiente",
        server_default=text("'pendiente'"),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "usuario_a <> usuario_b"
        ),
        CheckConstraint(
            "estado IN ('pendiente', 'aceptada', 'rechazada')"
        ),
    )

    usuario_a_rel = relationship(
        "Usuario",
        foreign_keys=[usuario_a],
        back_populates="conexiones_enviadas"
    )
    usuario_b_rel = relationship(
        "Usuario",
        foreign_keys=[usuario_b],
        back_populates="conexiones_recibidas"
    )
