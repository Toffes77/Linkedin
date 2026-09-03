from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from src.db.models.comentario_model import Comentario
from src.dtos.comentario_dto import GuardarComentarioDTO
from src.mappers.comentario_mapper import ComentarioMapper


class ComentarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: GuardarComentarioDTO) -> Comentario:
        comentario = ComentarioMapper.to_model(data)
        self.db.add(comentario)
        self.db.commit()
        comentario_creado = self.get_by_id(comentario.id)
        if comentario_creado is None:
            raise RuntimeError("No se pudo recuperar el comentario creado.")
        return comentario_creado

    def get_by_id(self, comentario_id: int) -> Comentario | None:
        return (
            self.db.query(Comentario)
            .options(joinedload(Comentario.autor))
            .filter(Comentario.id == comentario_id)
            .first()
        )

    def get_roots_page(
        self,
        publicacion_id: int,
        *,
        limit: int,
        after: tuple[datetime, int] | None = None,
    ) -> list[tuple[Comentario, int]]:
        query = self._with_direct_reply_count().filter(
            Comentario.publicacion_id == publicacion_id,
            Comentario.comentario_padre_id.is_(None),
        )
        if after is not None:
            fecha, comentario_id = after
            query = query.filter(
                or_(
                    Comentario.fecha < fecha,
                    and_(
                        Comentario.fecha == fecha,
                        Comentario.id < comentario_id,
                    ),
                )
            )
        return (
            query.order_by(Comentario.fecha.desc(), Comentario.id.desc())
            .limit(limit)
            .all()
        )

    def get_direct_replies_page(
        self,
        comentario_padre_id: int,
        *,
        limit: int,
        after: tuple[datetime, int] | None = None,
    ) -> list[tuple[Comentario, int]]:
        query = self._with_direct_reply_count().filter(
            Comentario.comentario_padre_id == comentario_padre_id,
        )
        if after is not None:
            fecha, comentario_id = after
            query = query.filter(
                or_(
                    Comentario.fecha > fecha,
                    and_(
                        Comentario.fecha == fecha,
                        Comentario.id > comentario_id,
                    ),
                )
            )
        return (
            query.order_by(Comentario.fecha.asc(), Comentario.id.asc())
            .limit(limit)
            .all()
        )

    def count_by_publicacion(self, publicacion_id: int) -> int:
        return (
            self.db.query(func.count(Comentario.id))
            .filter(Comentario.publicacion_id == publicacion_id)
            .scalar()
            or 0
        )

    def count_by_publicaciones(self, publicacion_ids: list[int]) -> dict[int, int]:
        if not publicacion_ids:
            return {}
        rows = (
            self.db.query(Comentario.publicacion_id, func.count(Comentario.id))
            .filter(Comentario.publicacion_id.in_(publicacion_ids))
            .group_by(Comentario.publicacion_id)
            .all()
        )
        return {publicacion_id: cantidad for publicacion_id, cantidad in rows}

    def delete(self, comentario: Comentario) -> None:
        self.db.delete(comentario)
        self.db.commit()

    def _with_direct_reply_count(self):
        child = aliased(Comentario)
        direct_reply_count = (
            select(func.count(child.id))
            .where(child.comentario_padre_id == Comentario.id)
            .correlate(Comentario)
            .scalar_subquery()
        )
        return (
            self.db.query(Comentario, direct_reply_count.label("cantidad_respuestas"))
            .options(joinedload(Comentario.autor))
        )
