from sqlalchemy import Column, Integer, String

from src.db.connection import Base

from sqlalchemy import Float



class Empresa(Base):
    __tablename__ = "Empresa"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    industria = Column(String(100))
    sitio_web = Column(String(255))


"""
CREATE TABLE Empresa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    industria VARCHAR(100),
    sitio_web VARCHAR(255)
);
"""