from sqlalchemy import Column, Integer, String, DateTime, text

from src.db.connection import Base


class Usuario(Base):
    __tablename__ = "Usuario"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    headline = Column(String(200), nullable=False)
    ciudad = Column(String(100), nullable=False)
    fecha_registro = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )