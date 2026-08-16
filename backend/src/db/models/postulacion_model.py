from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.db.connection import Base


class Postulacion(Base):
    __tablename__ = "postulacion"

    id = Column(Integer, primary_key=True)
    oferta_id = Column(Integer, ForeignKey("oferta.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)

    fecha = Column(DateTime, server_default=func.now(), nullable=False)

    estado = Column(
        String(20),
        default="nueva",
        server_default=text("'nueva'"),
        nullable=False
    )

    oferta = relationship("Oferta", back_populates="postulaciones")
    usuario = relationship("Usuario", back_populates="postulaciones")

    __table_args__ = (
        UniqueConstraint("oferta_id", "usuario_id"),
        CheckConstraint(
            "estado IN ('nueva', 'vista', 'entrevista', 'contratado', 'rechazada')"
        ),
    )
