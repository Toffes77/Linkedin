from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.db.models.oferta_model import Oferta
from src.dtos.oferta_dto import CreateOfertaDTO, UpdateOfertaDTO
from src.mappers.oferta_mapper import OfertaMapper


class OfertaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, oferta_data: CreateOfertaDTO) -> Oferta:
        oferta = OfertaMapper.to_model(oferta_data)
        self.db.add(oferta)
        self.db.commit()
        self.db.refresh(oferta)
        return oferta

    def get_by_id(self, oferta_id: int) -> Oferta | None:
        return self.db.get(Oferta, oferta_id)

    def get_by_empresa_page(
        self,
        empresa_id: int,
        *,
        published_only: bool,
        limit: int,
        after_id: int | None = None,
    ) -> list[Oferta]:
        query = self.db.query(Oferta).filter(Oferta.empresa_id == empresa_id)
        if published_only:
            query = query.filter(Oferta.publicada.is_(True))
        if after_id is not None:
            query = query.filter(Oferta.id < after_id)
        return query.order_by(Oferta.id.desc()).limit(limit).all()

    def get_publicadas(
        self,
        titulo: str | None = None,
        *,
        limit: int = 21,
        after: tuple[datetime, int] | None = None,
    ) -> list[Oferta]:
        query = self.db.query(Oferta).filter(Oferta.publicada.is_(True))
        if titulo:
            query = query.filter(Oferta.titulo.ilike(f"%{titulo}%"))
        if after is not None:
            fecha, oferta_id = after
            query = query.filter(
                or_(
                    Oferta.fecha_publicacion < fecha,
                    and_(
                        Oferta.fecha_publicacion == fecha,
                        Oferta.id < oferta_id,
                    ),
                )
            )
        return (
            query.order_by(Oferta.fecha_publicacion.desc(), Oferta.id.desc())
            .limit(limit)
            .all()
        )

    def update(
        self,
        oferta: Oferta,
        oferta_data: UpdateOfertaDTO,
        *,
        commit: bool = True,
    ) -> Oferta:
        OfertaMapper.apply_update(oferta, oferta_data)

        if commit:
            self.db.commit()
            self.db.refresh(oferta)
        else:
            self.db.flush()
        return oferta
