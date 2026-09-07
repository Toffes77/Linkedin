from enum import Enum

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.db.connection import Base


class TipoMultimedia(str, Enum):
    IMAGEN = "IMAGEN"
    VIDEO = "VIDEO"


class PublicacionMultimedia(Base):
    __tablename__ = "publicacion_multimedia"

    id = Column(Integer, primary_key=True)
    publicacion_id = Column(
        Integer,
        ForeignKey("publicacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    ruta = Column(String(255), nullable=False)
    tipo = Column(String(10), nullable=False)
    orden = Column(Integer, nullable=False)

    publicacion = relationship("Publicacion", back_populates="multimedia")

    __table_args__ = (
        CheckConstraint("tipo IN ('IMAGEN', 'VIDEO')", name="publicacion_multimedia_tipo_check"),
        CheckConstraint("orden >= 0", name="publicacion_multimedia_orden_check"),
        UniqueConstraint("publicacion_id", "orden", name="uq_publicacion_multimedia_orden"),
        Index("idx_publicacion_multimedia_publicacion", "publicacion_id", "orden"),
    )
