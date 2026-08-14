from sqlalchemy import Column, Integer, String, DateTime

from src.db.connection import Base

from sqlalchemy import Float

class Usuario(Base):
    __tablename__ = "Usuario"


    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    headline = Column(String(200), nullable=False)
    ciudad = Column(String(100), nullable=False)
    fecha_registro = Column(DateTime, nullable=False)


"""
CREATE TABLE Usuario (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    headline VARCHAR(200) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""