from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.db.connection import Base


POSTULACION_UNIQUE_CONSTRAINT = "postulacion_oferta_id_usuario_id_key"


class Postulacion(Base):
    __tablename__ = "postulacion"

    id = Column(Integer, primary_key=True)
    oferta_id = Column(Integer, ForeignKey("oferta.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)

    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    estado = Column(
        String(20),
        default="nueva",
        server_default=text("'nueva'"),
        nullable=False
    )

    oferta = relationship("Oferta", back_populates="postulaciones")
    usuario = relationship("Usuario", back_populates="postulaciones")

    __table_args__ = (
        UniqueConstraint(
            "oferta_id",
            "usuario_id",
            name=POSTULACION_UNIQUE_CONSTRAINT,
        ),
        CheckConstraint(
            "estado IN ('nueva', 'vista', 'entrevista', 'contratado', 'rechazada')"
        ),
        Index(
            "idx_postulacion_usuario_fecha_id",
            "usuario_id",
            fecha.desc(),
            id.desc(),
        ),
        Index(
            "idx_postulacion_oferta_fecha_id",
            "oferta_id",
            fecha.desc(),
            id.desc(),
        ),
    )
