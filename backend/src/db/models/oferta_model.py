from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from db.connection import Base


class Oferta(Base):
    __tablename__ = "Oferta"

    id = Column(Integer, primary_key=True)

    empresa_id = Column(
        Integer,
        ForeignKey("Empresa.id"),
        nullable=False
    )

    titulo = Column(String(200), nullable=False)

    descripcion = Column(Text, nullable=False)

    publicada = Column(
        Boolean,
        default=False,
        nullable=False
    )

    fecha_publicacion = Column(
        DateTime,
        nullable=True
    )