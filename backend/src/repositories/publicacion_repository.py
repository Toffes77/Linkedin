from dataclasses import dataclass

from sqlalchemy import BigInteger, and_, case, cast, extract, func, literal, or_, text
from sqlalchemy.orm import Session, joinedload

from src.db.models.publicacion_model import Publicacion
from src.dtos.publicacion_dto import CreatePublicacionDTO, UpdatePublicacionDTO
from src.mappers.publicacion_mapper import PublicacionMapper
from src.utils.feed_cursor import FeedPosition


@dataclass(frozen=True)
class FeedPageRow:
    publicacion: Publicacion
    position: FeedPosition


class PublicacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, publicacion_data: CreatePublicacionDTO) -> Publicacion:
        publicacion = PublicacionMapper.to_model(publicacion_data)
        self.db.add(publicacion)
        self.db.commit()
        created = self.get_by_id(publicacion.id)
        if created is None:
            raise RuntimeError("No se pudo recuperar la publicación creada.")
        return created

    def get_by_id(self, publicacion_id: int) -> Publicacion | None:
        return (
            self.db.query(Publicacion)
            .options(joinedload(Publicacion.autor))
            .filter(Publicacion.id == publicacion_id)
            .first()
        )

    def get_by_autor(
        self, autor_id: int, limit: int | None = None, offset: int = 0
    ) -> list[Publicacion]:
        query = (
            self.db.query(Publicacion)
            .options(joinedload(Publicacion.autor))
            .filter(Publicacion.autor_id == autor_id)
            .order_by(Publicacion.fecha.desc(), Publicacion.id.desc())
            .offset(offset)
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_max_id(self, visibility_snapshot: str | None = None) -> int:
        query = self.db.query(func.coalesce(func.max(Publicacion.id), 0))
        if visibility_snapshot is not None:
            query = query.filter(
                self._visibility_clause().params(
                    feed_visibility_snapshot=visibility_snapshot
                )
            )
        return query.scalar()

    def get_visibility_snapshot(self) -> str | None:
        if self.db.bind is None or self.db.bind.dialect.name != "postgresql":
            return None
        return self.db.execute(
            text("SELECT txid_current_snapshot()::text")
        ).scalar_one()

    def get_feed_page(
        self,
        social_author_ids: set[int],
        seed: int,
        snapshot_max_id: int,
        visibility_snapshot: str | None,
        limit: int,
        after: FeedPosition | None = None,
        excluded_publicacion_id: int | None = None,
    ) -> list[FeedPageRow]:
        author_rank = func.row_number().over(
            partition_by=Publicacion.autor_id,
            order_by=(Publicacion.fecha.desc(), Publicacion.id.desc()),
        )
        ranked_query = self.db.query(
            Publicacion.id.label("id"),
            Publicacion.autor_id.label("autor_id"),
            Publicacion.fecha.label("fecha"),
            author_rank.label("author_rank"),
        )
        ranked_query = ranked_query.filter(Publicacion.id <= snapshot_max_id)
        if visibility_snapshot is not None:
            ranked_query = ranked_query.filter(
                self._visibility_clause()
            ).params(feed_visibility_snapshot=visibility_snapshot)
        ranked_by_author = ranked_query.subquery("ranked_by_author")

        is_social = (
            case(
                (ranked_by_author.c.autor_id.in_(social_author_ids), 1),
                else_=0,
            )
            if social_author_ids
            else literal(0)
        )
        diversified = (
            self.db.query(
                ranked_by_author.c.id,
                ranked_by_author.c.fecha,
                is_social.label("is_social"),
            )
            .filter(ranked_by_author.c.author_rank <= 2)
            .subquery("diversified_feed")
        )

        stable_jitter = case(
            (
                diversified.c.is_social == 1,
                (
                    (cast(diversified.c.id, BigInteger) * 7919 + seed) % 15
                )
                - 7,
            ),
            else_=0,
        )
        day_key = (
            cast(extract("year", diversified.c.fecha), BigInteger) * 10_000
            + cast(extract("month", diversified.c.fecha), BigInteger) * 100
            + cast(extract("day", diversified.c.fecha), BigInteger)
        )

        query = (
            self.db.query(
                Publicacion,
                day_key.label("day_key"),
                diversified.c.is_social.label("is_social"),
                stable_jitter.label("jitter"),
                diversified.c.fecha.label("feed_fecha"),
            )
            .options(joinedload(Publicacion.autor))
            .join(diversified, Publicacion.id == diversified.c.id)
        )
        if excluded_publicacion_id is not None:
            query = query.filter(diversified.c.id != excluded_publicacion_id)
        if after is not None:
            query = query.filter(
                or_(
                    day_key < after.day_key,
                    and_(
                        day_key == after.day_key,
                        diversified.c.is_social < after.is_social,
                    ),
                    and_(
                        day_key == after.day_key,
                        diversified.c.is_social == after.is_social,
                        stable_jitter > after.jitter,
                    ),
                    and_(
                        day_key == after.day_key,
                        diversified.c.is_social == after.is_social,
                        stable_jitter == after.jitter,
                        diversified.c.fecha < after.fecha,
                    ),
                    and_(
                        day_key == after.day_key,
                        diversified.c.is_social == after.is_social,
                        stable_jitter == after.jitter,
                        diversified.c.fecha == after.fecha,
                        diversified.c.id < after.publicacion_id,
                    ),
                )
            )

        rows = (
            query.order_by(
                day_key.desc(),
                diversified.c.is_social.desc(),
                stable_jitter,
                diversified.c.fecha.desc(),
                diversified.c.id.desc(),
            )
            .limit(limit)
            .all()
        )
        return [
            FeedPageRow(
                publicacion=row[0],
                position=FeedPosition(
                    day_key=int(row.day_key),
                    is_social=int(row.is_social),
                    jitter=int(row.jitter),
                    fecha=row.feed_fecha,
                    publicacion_id=row[0].id,
                ),
            )
            for row in rows
        ]

    @staticmethod
    def _visibility_clause():
        return text(
            "txid_visible_in_snapshot("
            "publicacion.xmin::text::bigint, "
            "CAST(:feed_visibility_snapshot AS txid_snapshot)"
            ")"
        )

    def update(
        self,
        publicacion: Publicacion,
        publicacion_data: UpdatePublicacionDTO,
    ) -> Publicacion:
        PublicacionMapper.apply_update(publicacion, publicacion_data)

        self.db.commit()
        updated = self.get_by_id(publicacion.id)
        if updated is None:
            raise RuntimeError("No se pudo recuperar la publicación actualizada.")
        return updated

    def delete(self, publicacion: Publicacion) -> None:
        self.db.delete(publicacion)
        self.db.commit()
