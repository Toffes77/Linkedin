from sqlalchemy import Column, Integer, String, Date, ForeignKey, CheckConstraint

from src.db.connection import Base


class Experiencia(Base):
    __tablename__ = "Experiencia"

    id = Column(Integer, primary_key=True)

    usuario_id = Column(
        Integer,
        ForeignKey("Usuario.id"),
        nullable=False
    )

    empresa_id = Column(
        Integer,
        ForeignKey("Empresa.id"),
        nullable=False
    )

    puesto = Column(String(100), nullable=False)

    desde = Column(Date, nullable=False)

    hasta = Column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "hasta IS NULL OR desde <= hasta",
            name="check_fechas_experiencia"
        ),
    )