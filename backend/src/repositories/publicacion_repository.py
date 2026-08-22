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

    def get_recent_by_authors(
        self, autor_ids: set[int], limit: int
    ) -> list[Publicacion]:
        if not autor_ids or limit <= 0:
            return []
        return (
            self.db.query(Publicacion)
            .filter(Publicacion.autor_id.in_(autor_ids))
            .order_by(Publicacion.fecha.desc(), Publicacion.id.desc())
            .limit(limit)
            .all()
        )

    def get_general(
        self,
        excluded_ids: set[int],
        excluded_author_id: int,
        limit: int,
        offset: int,
    ) -> list[Publicacion]:
        query = (
            self.db.query(Publicacion)
            .filter(Publicacion.autor_id != excluded_author_id)
        )
        if excluded_ids:
            query = query.filter(Publicacion.id.not_in(excluded_ids))
        return (
            query.order_by(Publicacion.fecha.desc(), Publicacion.id.desc())
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
