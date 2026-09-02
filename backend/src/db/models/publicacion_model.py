from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.connection import Base


class Publicacion(Base):
    __tablename__ = "publicacion"

    id = Column(Integer, primary_key=True)

    autor_id = Column(
        Integer,
        ForeignKey("usuario.id"),
        nullable=False
    )

    texto = Column(String(3000), nullable=False)

    fecha = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    autor = relationship("Usuario", back_populates="publicaciones")
    reacciones = relationship(
        "Reacciones",
        back_populates="publicacion",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    comentarios = relationship(
        "Comentario",
        back_populates="publicacion",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "LENGTH(texto) BETWEEN 1 AND 3000 "
            "AND texto ~ '[^[:space:]]'",
            name="check_longitud_texto"
        ).ddl_if(dialect="postgresql"),
        Index(
            "idx_publicacion_autor_fecha_id",
            "autor_id",
            fecha.desc(),
            id.desc(),
        ),
    )
