from sqlalchemy import Column, Integer, String, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from src.db.connection import Base


class Experiencia(Base):
    __tablename__ = "experiencia"

    id = Column(Integer, primary_key=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id"),
        nullable=False
    )

    empresa_id = Column(
        Integer,
        ForeignKey("empresa.id"),
        nullable=False
    )

    puesto = Column(String(100), nullable=False)

    desde = Column(Date, nullable=False)

    hasta = Column(Date, nullable=True)

    usuario = relationship("Usuario", back_populates="experiencias")
    empresa = relationship("Empresa", back_populates="experiencias")

    __table_args__ = (
        CheckConstraint(
            "hasta IS NULL OR desde <= hasta",
            name="check_fechas_experiencia"
        ),
    )
