from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, CheckConstraint
from sqlalchemy.sql import func
from db.connection import Base


class Conexion(Base):
    __tablename__ = "conexiones"

    usuario_a = Column(
        Integer,
        ForeignKey("Usuario.id"),
        primary_key=True,
        nullable=False
    )

    usuario_b = Column(
        Integer,
        ForeignKey("Usuario.id"),
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