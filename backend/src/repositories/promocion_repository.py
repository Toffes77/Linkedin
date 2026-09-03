from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from src.db.models.promocion_model import Promocion
from src.db.models.solicitud_contratacion_promocion_model import SolicitudContratacionPromocion


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

    def get_by_id(self, promocion_id: int) -> Promocion | None:
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

    def get_public_page(
        self,
        current_user_id: int,
        *,
        title: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Promocion], int]:
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
            .filter(ranked.c.position == 1)
        )
        if title:
            query = query.filter(Promocion.titulo.ilike(f"%{title}%"))

        total = query.order_by(None).count()
        items = (
            query.order_by(Promocion.fecha_creacion.desc(), Promocion.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

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
