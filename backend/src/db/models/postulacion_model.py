from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from db.connection import Base


class Postulacion(Base):
    _tablename_ = "postulaciones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    oferta_id = Column(Integer, ForeignKey("ofertas.id"), nullable=False)
    estado = Column(String, default="Pendiente", nullable=False)
    fecha_postulacion = Column(DateTime, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)