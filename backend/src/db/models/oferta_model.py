from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship

from src.db.connection import Base


class Oferta(Base):
    __tablename__ = "oferta"

    id = Column(Integer, primary_key=True)

    empresa_id = Column(
        Integer,
        ForeignKey("empresa.id"),
        nullable=False
    )

    titulo = Column(String(200), nullable=False)

    descripcion = Column(Text, nullable=False)

    publicada = Column(
        Boolean,
        default=False,
        server_default=text("FALSE"),
        nullable=False
    )

    fecha_publicacion = Column(
        DateTime,
        nullable=True
    )

    empresa = relationship("Empresa", back_populates="ofertas")
    postulaciones = relationship("Postulacion", back_populates="oferta")
