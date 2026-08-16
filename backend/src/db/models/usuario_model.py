from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.orm import relationship

from src.db.connection import Base


class Usuario(Base):
    __tablename__ = "usuario"

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

    experiencias = relationship("Experiencia", back_populates="usuario")
    publicaciones = relationship("Publicacion", back_populates="autor")
    postulaciones = relationship("Postulacion", back_populates="usuario")
    reacciones = relationship("Reacciones", back_populates="usuario")
    conexiones_enviadas = relationship(
        "Conexion",
        foreign_keys="Conexion.usuario_a",
        back_populates="usuario_a_rel"
    )
    conexiones_recibidas = relationship(
        "Conexion",
        foreign_keys="Conexion.usuario_b",
        back_populates="usuario_b_rel"
    )
