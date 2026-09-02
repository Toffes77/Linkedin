from sqlalchemy import CheckConstraint, Column, Integer, String
from sqlalchemy.orm import relationship

from src.db.connection import Base

class Empresa(Base):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    industria = Column(String(100))
    sitio_web = Column(String(255))
    foto_perfil_url = Column(String(255), nullable=True)

    experiencias = relationship("Experiencia", back_populates="empresa")
    ofertas = relationship("Oferta", back_populates="empresa")
    usuarios_empresa = relationship(
        "EmpresaUsuario",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    solicitudes_contratacion_promocion = relationship(
        "SolicitudContratacionPromocion",
        back_populates="empresa",
    )

    __table_args__ = (
        CheckConstraint(
            "nombre ~ '[^[:space:]]'",
            name="empresa_nombre_no_blank_check",
        ).ddl_if(dialect="postgresql"),
    )
