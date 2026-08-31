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

    def get_by_empresa(self, empresa_id: int) -> list[Oferta]:
        return (
            self.db.query(Oferta)
            .filter(Oferta.empresa_id == empresa_id)
            .all()
        )

    def get_publicadas_by_empresa(self, empresa_id: int) -> list[Oferta]:
        return (
            self.db.query(Oferta)
            .filter(
                Oferta.empresa_id == empresa_id,
                Oferta.publicada.is_(True),
            )
            .all()
        )

    def get_publicadas(self, titulo: str | None = None) -> list[Oferta]:
        query = self.db.query(Oferta).filter(Oferta.publicada.is_(True))
        if titulo:
            query = query.filter(Oferta.titulo.ilike(f"%{titulo}%"))
        return query.all()

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
