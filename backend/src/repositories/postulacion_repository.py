from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from src.db.models.postulacion_model import Postulacion
from src.dtos.postulacion_dto import CreatePostulacionDTO, UpdatePostulacionDTO
from src.mappers.postulacion_mapper import PostulacionMapper


class PostulacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        postulacion_data: CreatePostulacionDTO,
        *,
        commit: bool = True,
    ) -> Postulacion:
        postulacion = PostulacionMapper.to_model(postulacion_data)
        self.db.add(postulacion)
        if commit:
            self.db.commit()
            self.db.refresh(postulacion)
        else:
            self.db.flush()
        return postulacion

    def get_by_id(self, postulacion_id: int) -> Postulacion | None:
        return (
            self.db.query(Postulacion)
            .options(joinedload(Postulacion.oferta))
            .filter(Postulacion.id == postulacion_id)
            .first()
        )

    def get_by_id_for_update(self, postulacion_id: int) -> Postulacion | None:
        return (
            self.db.query(Postulacion)
            .populate_existing()
            .filter(Postulacion.id == postulacion_id)
            .with_for_update(of=Postulacion)
            .first()
        )

    def get_by_oferta_page(
        self,
        oferta_id: int,
        *,
        limit: int,
        after: tuple[datetime, int] | None = None,
    ) -> list[Postulacion]:
        query = (
            self.db.query(Postulacion)
            .options(joinedload(Postulacion.oferta))
            .filter(Postulacion.oferta_id == oferta_id)
        )
        return self._ordered_page(query, limit=limit, after=after)

    def get_by_usuario_page(
        self,
        usuario_id: int,
        *,
        oferta_id: int | None,
        limit: int,
        after: tuple[datetime, int] | None = None,
    ) -> list[Postulacion]:
        query = (
            self.db.query(Postulacion)
            .options(joinedload(Postulacion.oferta))
            .filter(Postulacion.usuario_id == usuario_id)
        )
        if oferta_id is not None:
            query = query.filter(Postulacion.oferta_id == oferta_id)
        return self._ordered_page(query, limit=limit, after=after)

    def get_by_oferta_and_usuario(
        self,
        oferta_id: int,
        usuario_id: int,
    ) -> Postulacion | None:
        return (
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == oferta_id,
                Postulacion.usuario_id == usuario_id,
            )
            .first()
        )

    def update(
        self,
        postulacion: Postulacion,
        postulacion_data: UpdatePostulacionDTO,
        *,
        commit: bool = True,
    ) -> Postulacion:
        PostulacionMapper.apply_update(postulacion, postulacion_data)

        if commit:
            self.db.commit()
            self.db.refresh(postulacion)
        else:
            self.db.flush()
        return postulacion

    def count_by_oferta(self, oferta_id: int) -> int:
        return (
            self.db.query(func.count(Postulacion.id))
            .filter(Postulacion.oferta_id == oferta_id)
            .scalar()
        )

    def count_by_oferta_and_estado(self, oferta_id: int, estado: str) -> int:
        return (
            self.db.query(func.count(Postulacion.id))
            .filter(
                Postulacion.oferta_id == oferta_id,
                Postulacion.estado == estado,
            )
            .scalar()
        )

    def count_grouped_by_estado(self, oferta_id: int) -> list[tuple[str, int]]:
        return (
            self.db.query(Postulacion.estado, func.count(Postulacion.id))
            .filter(Postulacion.oferta_id == oferta_id)
            .group_by(Postulacion.estado)
            .all()
        )

    @staticmethod
    def _ordered_page(query, *, limit: int, after: tuple[datetime, int] | None):
        if after is not None:
            fecha, postulacion_id = after
            query = query.filter(
                or_(
                    Postulacion.fecha < fecha,
                    and_(
                        Postulacion.fecha == fecha,
                        Postulacion.id < postulacion_id,
                    ),
                )
            )
        return (
            query.order_by(Postulacion.fecha.desc(), Postulacion.id.desc())
            .limit(limit)
            .all()
        )
