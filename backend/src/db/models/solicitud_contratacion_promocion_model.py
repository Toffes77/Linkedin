from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, text
from sqlalchemy.orm import relationship

from src.db.connection import Base


class EstadoSolicitudContratacionPromocion(str, Enum):
    PENDIENTE = "PENDIENTE"
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"


class SolicitudContratacionPromocion(Base):
    __tablename__ = "solicitud_contratacion_promocion"

    id = Column(Integer, primary_key=True)
    promocion_id = Column(
        Integer,
        ForeignKey("promocion.id", ondelete="CASCADE"),
        nullable=False,
    )
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    solicitante_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    estado = Column(
        SqlEnum(
            EstadoSolicitudContratacionPromocion,
            name="estado_solicitud_contratacion_promocion",
        ),
        nullable=False,
        default=EstadoSolicitudContratacionPromocion.PENDIENTE,
        server_default=EstadoSolicitudContratacionPromocion.PENDIENTE.value,
    )
    fecha_creacion = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    fecha_respuesta = Column(DateTime, nullable=True)

    promocion = relationship("Promocion", back_populates="solicitudes_contratacion")
    empresa = relationship("Empresa", back_populates="solicitudes_contratacion_promocion")
    solicitante = relationship(
        "Usuario",
        foreign_keys=[solicitante_id],
        back_populates="solicitudes_contratacion_iniciadas",
    )

    __table_args__ = (
        Index(
            "uq_solicitud_promocion_empresa_pendiente",
            "promocion_id",
            "empresa_id",
            unique=True,
            postgresql_where=text("estado = 'PENDIENTE'"),
            sqlite_where=text("estado = 'PENDIENTE'"),
        ),
        Index(
            "idx_solicitud_promocion_estado",
            "promocion_id",
            "estado",
            fecha_creacion.desc(),
        ),
    )
