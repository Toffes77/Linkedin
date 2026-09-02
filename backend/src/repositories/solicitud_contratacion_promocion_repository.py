from sqlalchemy.orm import Session, joinedload

from src.db.models.solicitud_contratacion_promocion_model import (
    EstadoSolicitudContratacionPromocion,
    SolicitudContratacionPromocion,
)
from src.utils.datetime_utils import utc_now


class SolicitudContratacionPromocionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        request: SolicitudContratacionPromocion,
        *,
        commit: bool = True,
    ) -> SolicitudContratacionPromocion:
        self.db.add(request)
        if commit:
            self.db.commit()
            self.db.refresh(request)
        else:
            self.db.flush()
        return request

    def get_pending(
        self,
        promocion_id: int,
        empresa_id: int,
    ) -> SolicitudContratacionPromocion | None:
        return (
            self.db.query(SolicitudContratacionPromocion)
            .filter(
                SolicitudContratacionPromocion.promocion_id == promocion_id,
                SolicitudContratacionPromocion.empresa_id == empresa_id,
                SolicitudContratacionPromocion.estado
                == EstadoSolicitudContratacionPromocion.PENDIENTE,
            )
            .first()
        )

    def get_by_id_for_update(
        self,
        request_id: int,
    ) -> SolicitudContratacionPromocion | None:
        return (
            self.db.query(SolicitudContratacionPromocion)
            .filter(SolicitudContratacionPromocion.id == request_id)
            .with_for_update()
            .first()
        )

    def get_by_id(self, request_id: int) -> SolicitudContratacionPromocion | None:
        return (
            self.db.query(SolicitudContratacionPromocion)
            .options(
                joinedload(SolicitudContratacionPromocion.promocion),
                joinedload(SolicitudContratacionPromocion.empresa),
            )
            .filter(SolicitudContratacionPromocion.id == request_id)
            .first()
        )

    def accept(
        self,
        request: SolicitudContratacionPromocion,
        *,
        commit: bool = True,
    ) -> SolicitudContratacionPromocion:
        request.estado = EstadoSolicitudContratacionPromocion.ACEPTADA
        request.fecha_respuesta = utc_now()
        if commit:
            self.db.commit()
            self.db.refresh(request)
        else:
            self.db.flush()
        return request
