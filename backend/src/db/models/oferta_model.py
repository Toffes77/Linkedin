from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
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
        DateTime(timezone=True),
        nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "titulo ~ '[^[:space:]]'",
            name="oferta_titulo_no_blank_check",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "descripcion ~ '[^[:space:]]'",
            name="oferta_descripcion_no_blank_check",
        ).ddl_if(dialect="postgresql"),
        Index(
            "idx_oferta_publicada_fecha_id",
            fecha_publicacion.desc(),
            id.desc(),
            postgresql_where=publicada.is_(True),
        ),
        Index("idx_oferta_empresa_id", "empresa_id", id.desc()),
    )

    empresa = relationship("Empresa", back_populates="ofertas")
    postulaciones = relationship("Postulacion", back_populates="oferta")
