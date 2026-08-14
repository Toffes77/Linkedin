from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from db.connection import Base


class Postulacion(Base):
    __tablename__ = "Postulacion"

    id = Column(Integer, primary_key=True)
    oferta_id = Column(Integer, ForeignKey("Oferta.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("Usuario.id"), nullable=False)

    fecha = Column(DateTime, server_default=func.now(), nullable=False)

    estado = Column(String(20), default="nueva", nullable=False)

    __table_args__ = (
        UniqueConstraint("oferta_id", "usuario_id"),
        CheckConstraint(
            "estado IN ('nueva', 'vista', 'entrevista', 'contratado', 'rechazada')"
        ),
    )