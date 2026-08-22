from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.connection import Base


class Seguimiento(Base):
    __tablename__ = "seguimiento"

    seguidor_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    seguido_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    fecha = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (CheckConstraint("seguidor_id <> seguido_id"),)

    seguidor = relationship(
        "Usuario", foreign_keys=[seguidor_id], back_populates="seguimientos_realizados"
    )
    seguido = relationship(
        "Usuario", foreign_keys=[seguido_id], back_populates="seguidores"
    )
