from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import relationship

from src.db.connection import Base


class Promocion(Base):
    __tablename__ = "promocion"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(
        Integer,
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    titulo = Column(String(160), nullable=False)
    descripcion = Column(Text, nullable=False)
    fecha_creacion = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    usuario = relationship("Usuario", back_populates="promociones")
    solicitudes_contratacion = relationship(
        "SolicitudContratacionPromocion",
        back_populates="promocion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SolicitudContratacionPromocion.fecha_creacion.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(titulo)) BETWEEN 1 AND 160",
            name="promocion_titulo_check",
        ),
        CheckConstraint(
            "length(trim(descripcion)) BETWEEN 1 AND 3000",
            name="promocion_descripcion_check",
        ),
        Index(
            "idx_promocion_usuario_fecha",
            "usuario_id",
            fecha_creacion.desc(),
            id.desc(),
        ),
        Index("idx_promocion_fecha", fecha_creacion.desc(), id.desc()),
    )
