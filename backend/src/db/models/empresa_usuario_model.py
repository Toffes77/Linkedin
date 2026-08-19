from enum import Enum

from sqlalchemy import Column, Enum as SqlEnum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from src.db.connection import Base


class RolEmpresa(str, Enum):
    OWNER = "OWNER"
    RECRUITER = "RECRUITER"


class EmpresaUsuario(Base):
    __tablename__ = "empresa_usuario"

    empresa_id = Column(
        Integer,
        ForeignKey("empresa.id"),
        primary_key=True,
        nullable=False,
    )
    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id"),
        primary_key=True,
        nullable=False,
    )
    rol = Column(
        SqlEnum(RolEmpresa, name="rol_empresa"),
        nullable=False,
    )

    empresa = relationship("Empresa", back_populates="usuarios_empresa")
    usuario = relationship("Usuario", back_populates="empresas_usuario")
