from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.connection import Base


class Publicacion(Base):
    __tablename__ = "publicacion"

    id = Column(Integer, primary_key=True)

    autor_id = Column(
        Integer,
        ForeignKey("usuario.id"),
        nullable=False
    )

    texto = Column(String(3000), nullable=False)

    fecha = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    autor = relationship("Usuario", back_populates="publicaciones")
    reacciones = relationship("Reacciones", back_populates="publicacion")

    __table_args__ = (
        CheckConstraint(
            "LENGTH(texto) BETWEEN 1 AND 3000",
            name="check_longitud_texto"
        ),
    )
