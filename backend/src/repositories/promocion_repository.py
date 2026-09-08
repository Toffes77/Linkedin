from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from src.db.models.promocion_model import Promocion
from src.db.models.solicitud_contratacion_promocion_model import (
    EstadoSolicitudContratacionPromocion,
    SolicitudContratacionPromocion,
)


class PromocionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, promocion: Promocion, *, commit: bool = True) -> Promocion:
        self.db.add(promocion)
        if commit:
            self.db.commit()
            self.db.refresh(promocion)
        else:
            self.db.flush()
        return promocion

    def get_by_id_basic(
        self,
        promocion_id: int,
        *,
        for_update: bool = False,
    ) -> Promocion | None:
        query = (
            self.db.query(Promocion)
            .options(joinedload(Promocion.usuario))
            .filter(Promocion.id == promocion_id)
        )
        if for_update:
            query = query.with_for_update(of=Promocion)
        return query.first()

    def get_by_id_with_requests(self, promocion_id: int) -> Promocion | None:
        return (
            self.db.query(Promocion)
            .options(
                joinedload(Promocion.usuario),
                joinedload(Promocion.solicitudes_contratacion).joinedload(
                    SolicitudContratacionPromocion.empresa
                ),
            )
            .filter(Promocion.id == promocion_id)
            .first()
        )

    def get_by_id(self, promocion_id: int) -> Promocion | None:
        """Compatibilidad para consumidores que necesitan las solicitudes."""
        return self.get_by_id_with_requests(promocion_id)

    def get_board_page(
        self,
        current_user_id: int,
        *,
        title: str | None,
        limit: int,
        after: tuple[datetime, int] | None = None,
    ) -> list[Promocion]:
        ranked = (
            self.db.query(
                Promocion.id.label("promocion_id"),
                func.row_number().over(
                    partition_by=Promocion.usuario_id,
                    order_by=(Promocion.fecha_creacion.desc(), Promocion.id.desc()),
                ).label("position"),
            )
            .filter(Promocion.usuario_id != current_user_id)
            .subquery()
        )
        query = (
            self.db.query(Promocion)
            .join(ranked, ranked.c.promocion_id == Promocion.id)
            .options(joinedload(Promocion.usuario))
            .filter(
                ranked.c.position == 1,
                ~Promocion.solicitudes_contratacion.any(
                    SolicitudContratacionPromocion.estado
                    == EstadoSolicitudContratacionPromocion.ACEPTADA
                ),
            )
        )
        if title:
            escaped_title = (
                title.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            query = query.filter(
                Promocion.titulo.ilike(f"%{escaped_title}%", escape="\\")
            )

        if after is not None:
            fecha, promocion_id = after
            query = query.filter(
                or_(
                    Promocion.fecha_creacion < fecha,
                    and_(
                        Promocion.fecha_creacion == fecha,
                        Promocion.id < promocion_id,
                    ),
                )
            )
        return (
            query.order_by(Promocion.fecha_creacion.desc(), Promocion.id.desc())
            .limit(limit)
            .all()
        )

    def get_by_user_page(
        self,
        usuario_id: int,
        *,
        limit: int,
        after: tuple[datetime, int] | None = None,
    ) -> list[Promocion]:
        query = (
            self.db.query(Promocion)
            .options(
                joinedload(Promocion.usuario),
                joinedload(Promocion.solicitudes_contratacion).joinedload(
                    SolicitudContratacionPromocion.empresa
                ),
            )
            .filter(Promocion.usuario_id == usuario_id)
        )
        if after is not None:
            fecha, promocion_id = after
            query = query.filter(
                or_(
                    Promocion.fecha_creacion < fecha,
                    and_(
                        Promocion.fecha_creacion == fecha,
                        Promocion.id < promocion_id,
                    ),
                )
            )
        return (
            query.order_by(Promocion.fecha_creacion.desc(), Promocion.id.desc())
            .limit(limit)
            .all()
        )
