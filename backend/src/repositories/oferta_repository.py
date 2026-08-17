from sqlalchemy.orm import Session

from src.db.models.oferta_model import Oferta
from src.dtos.oferta_dto import CreateOfertaDTO, UpdateOfertaDTO


class OfertaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, oferta_data: CreateOfertaDTO) -> Oferta:
        oferta = Oferta(**oferta_data.model_dump())
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

    def get_publicadas(self) -> list[Oferta]:
        return (
            self.db.query(Oferta)
            .filter(Oferta.publicada.is_(True))
            .all()
        )

    def update(self, oferta: Oferta, oferta_data: UpdateOfertaDTO) -> Oferta:
        for field, value in oferta_data.model_dump(exclude_unset=True).items():
            setattr(oferta, field, value)

        self.db.commit()
        self.db.refresh(oferta)
        return oferta
