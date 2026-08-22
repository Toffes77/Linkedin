from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from src.db.connection import Base


class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    tipo = Column(String(30), nullable=False)
    mensaje = Column(String(500), nullable=False)
    leida = Column(Boolean, nullable=False, default=False, server_default="false")
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    postulacion_id = Column(Integer, ForeignKey("postulacion.id"), nullable=True)
    oferta_id = Column(Integer, ForeignKey("oferta.id"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('POSTULACION_NUEVA', 'POSTULACION_ESTADO')"
        ),
    )
