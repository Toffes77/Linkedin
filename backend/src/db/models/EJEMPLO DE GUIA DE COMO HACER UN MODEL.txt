from sqlalchemy import Column, Integer, String

from src.db.connection import Base

from sqlalchemy import Float

class Conductores(Base):
    __tablename__ = "conductores"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    licencia = Column(String, unique=True, nullable=False)
    calificacion_promedio = Column(Float, nullable=False)

