from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func

from src.db.connection import Base


class Publicacion(Base):
    __tablename__ = "Publicacion"

    id = Column(Integer, primary_key=True)

    autor_id = Column(
        Integer,
        ForeignKey("Usuario.id"),
        nullable=False
    )

    texto = Column(String(3000), nullable=False)

    fecha = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "LENGTH(texto) BETWEEN 1 AND 3000",
            name="check_longitud_texto"
        ),
    )