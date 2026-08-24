from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.connection import Base


class Comentario(Base):
    __tablename__ = "comentario"

    id = Column(Integer, primary_key=True)
    publicacion_id = Column(
        Integer,
        ForeignKey("publicacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    contenido = Column(String(1000), nullable=False)
    fecha = Column(DateTime, server_default=func.now(), nullable=False)
    comentario_padre_id = Column(
        Integer,
        ForeignKey("comentario.id", ondelete="CASCADE"),
        nullable=True,
    )

    publicacion = relationship("Publicacion", back_populates="comentarios")
    autor = relationship("Usuario", back_populates="comentarios")
    comentario_padre = relationship(
        "Comentario",
        remote_side=[id],
        back_populates="respuestas",
        foreign_keys=[comentario_padre_id],
    )
    respuestas = relationship(
        "Comentario",
        back_populates="comentario_padre",
        foreign_keys=[comentario_padre_id],
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=lambda: (Comentario.fecha.asc(), Comentario.id.asc()),
    )

    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(contenido)) BETWEEN 1 AND 1000",
            name="comentario_contenido_check",
        ),
        Index("idx_comentario_publicacion_fecha", "publicacion_id", "fecha"),
        Index("idx_comentario_padre_fecha", "comentario_padre_id", "fecha"),
    )
