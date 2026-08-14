from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from db.connection import Base


class Reacciones(Base):
    __tablename__ = "reacciones"

    usuario_id = Column(
        Integer,
        ForeignKey("Usuario.id"),
        primary_key=True,
        nullable=False
    )

    publicacion_id = Column(
        Integer,
        ForeignKey("Publicacion.id"),
        primary_key=True,
        nullable=False
    )

    tipo = Column(
        String(20),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('like', 'celebrar', 'apoyar', 'interesante')"
        ),
    )