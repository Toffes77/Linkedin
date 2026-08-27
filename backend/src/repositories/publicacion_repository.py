from sqlalchemy import BigInteger, case, cast, func, literal
from sqlalchemy.orm import Session

from src.db.models.publicacion_model import Publicacion
from src.dtos.publicacion_dto import CreatePublicacionDTO, UpdatePublicacionDTO
from src.mappers.publicacion_mapper import PublicacionMapper


class PublicacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, publicacion_data: CreatePublicacionDTO) -> Publicacion:
        publicacion = PublicacionMapper.to_model(publicacion_data)
        self.db.add(publicacion)
        self.db.commit()
        self.db.refresh(publicacion)
        return publicacion

    def get_by_id(self, publicacion_id: int) -> Publicacion | None:
        return self.db.get(Publicacion, publicacion_id)

    def get_by_autor(
        self, autor_id: int, limit: int | None = None, offset: int = 0
    ) -> list[Publicacion]:
        query = (
            self.db.query(Publicacion)
            .filter(Publicacion.autor_id == autor_id)
            .order_by(Publicacion.fecha.desc(), Publicacion.id.desc())
            .offset(offset)
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_feed(
        self,
        social_author_ids: set[int],
        seed: int,
        limit: int,
        offset: int,
    ) -> list[Publicacion]:
        author_rank = func.row_number().over(
            partition_by=Publicacion.autor_id,
            order_by=(Publicacion.fecha.desc(), Publicacion.id.desc()),
        )
        ranked_by_author = self.db.query(
            Publicacion.id.label("id"),
            Publicacion.autor_id.label("autor_id"),
            Publicacion.fecha.label("fecha"),
            author_rank.label("author_rank"),
        ).subquery("ranked_by_author")

        is_social = (
            case(
                (ranked_by_author.c.autor_id.in_(social_author_ids), 1),
                else_=0,
            )
            if social_author_ids
            else literal(0)
        )
        stream_rank = func.row_number().over(
            partition_by=is_social,
            order_by=(
                ranked_by_author.c.fecha.desc(),
                ranked_by_author.c.id.desc(),
            ),
        )
        diversified = (
            self.db.query(
                ranked_by_author.c.id,
                ranked_by_author.c.fecha,
                is_social.label("is_social"),
                stream_rank.label("stream_rank"),
            )
            .filter(ranked_by_author.c.author_rank <= 2)
            .subquery("diversified_feed")
        )

        stable_jitter = (
            (cast(diversified.c.id, BigInteger) * 7919 + seed) % 15
        ) - 7
        feed_position = case(
            (
                diversified.c.is_social == 1,
                diversified.c.stream_rank * 20 + stable_jitter,
            ),
            else_=diversified.c.stream_rank * 5,
        )

        return (
            self.db.query(Publicacion)
            .join(diversified, Publicacion.id == diversified.c.id)
            .order_by(
                feed_position,
                diversified.c.fecha.desc(),
                diversified.c.id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update(
        self,
        publicacion: Publicacion,
        publicacion_data: UpdatePublicacionDTO,
    ) -> Publicacion:
        PublicacionMapper.apply_update(publicacion, publicacion_data)

        self.db.commit()
        self.db.refresh(publicacion)
        return publicacion

    def delete(self, publicacion: Publicacion) -> None:
        self.db.delete(publicacion)
        self.db.commit()
