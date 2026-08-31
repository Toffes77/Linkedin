from sqlalchemy import Column, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import relationship

from src.db.connection import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False)
    nombre = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    headline = Column(String(200), nullable=False)
    ciudad = Column(String(100), nullable=False)
    foto_perfil_url = Column(String(255), nullable=True)
    fecha_registro = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )

    experiencias = relationship("Experiencia", back_populates="usuario")
    publicaciones = relationship("Publicacion", back_populates="autor")
    postulaciones = relationship("Postulacion", back_populates="usuario")
    reacciones = relationship("Reacciones", back_populates="usuario")
    comentarios = relationship(
        "Comentario",
        back_populates="autor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conexiones_lado_a = relationship(
        "Conexion",
        foreign_keys="Conexion.usuario_a",
        back_populates="usuario_a_rel"
    )
    conexiones_lado_b = relationship(
        "Conexion",
        foreign_keys="Conexion.usuario_b",
        back_populates="usuario_b_rel"
    )
    solicitudes_conexion_enviadas = relationship(
        "Conexion",
        foreign_keys="Conexion.solicitante_id",
        back_populates="solicitante_rel",
    )
    seguimientos_realizados = relationship(
        "Seguimiento",
        foreign_keys="Seguimiento.seguidor_id",
        back_populates="seguidor",
        cascade="all, delete-orphan",
    )
    seguidores = relationship(
        "Seguimiento",
        foreign_keys="Seguimiento.seguido_id",
        back_populates="seguido",
        cascade="all, delete-orphan",
    )
    empresas_usuario = relationship(
        "EmpresaUsuario",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    promociones = relationship(
        "Promocion",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    solicitudes_contratacion_iniciadas = relationship(
        "SolicitudContratacionPromocion",
        foreign_keys="SolicitudContratacionPromocion.solicitante_id",
        back_populates="solicitante",
    )
    conversaciones = relationship(
        "ConversacionUsuario",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("uq_usuario_email_lower", func.lower(email), unique=True),
    )
