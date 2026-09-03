from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import relationship

from src.db.connection import Base


REACCIONES_UNIQUE_CONSTRAINT = "reacciones_pkey"


class Reacciones(Base):
    __tablename__ = "reacciones"

    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id"),
        primary_key=True,
        nullable=False
    )

    publicacion_id = Column(
        Integer,
        ForeignKey("publicacion.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )

    tipo = Column(
        String(20),
        nullable=False
    )

    usuario = relationship("Usuario", back_populates="reacciones")
    publicacion = relationship("Publicacion", back_populates="reacciones")

    __table_args__ = (
        PrimaryKeyConstraint(name=REACCIONES_UNIQUE_CONSTRAINT),
        CheckConstraint(
            "tipo IN ('like', 'celebrar', 'apoyar', 'interesante')"
        ),
        Index("idx_reacciones_publicacion_tipo", "publicacion_id", "tipo"),
    )
