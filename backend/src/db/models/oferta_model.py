from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from db.connection import Base


class Oferta(Base):
    _tablename_ = "ofertas"

    id = Column(Integer, primary_key=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    empresa = Column(String, nullable=False)
    ubicacion = Column(String, nullable=False)
    modalidad = Column(String, nullable=False)
    salario = Column(Integer, nullable=True)
    estado = Column(String, default="Activa", nullable=False)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)