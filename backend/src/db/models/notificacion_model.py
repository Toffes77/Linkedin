from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from src.db.connection import Base


class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    tipo = Column(String(30), nullable=False)
    mensaje = Column(String(500), nullable=False)
    leida = Column(Boolean, nullable=False, default=False, server_default="false")
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    postulacion_id = Column(Integer, ForeignKey("postulacion.id"), nullable=True)
    oferta_id = Column(Integer, ForeignKey("oferta.id"), nullable=True)
    usuario_origen_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    promocion_id = Column(
        Integer,
        ForeignKey("promocion.id", ondelete="SET NULL"),
        nullable=True,
    )
    solicitud_contratacion_promocion_id = Column(
        Integer,
        ForeignKey("solicitud_contratacion_promocion.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('POSTULACION_NUEVA', 'POSTULACION_ESTADO', "
            "'NUEVO_SEGUIDOR', 'NUEVA_INVITACION_CONEXION', "
            "'CONEXION_ACEPTADA', 'CONTRATACION_PROMOCION')",
            name="notificacion_tipo_check",
        ),
    )
