from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.db.connection import Base

class Empresa(Base):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    industria = Column(String(100))
    sitio_web = Column(String(255))

    experiencias = relationship("Experiencia", back_populates="empresa")
    ofertas = relationship("Oferta", back_populates="empresa")
