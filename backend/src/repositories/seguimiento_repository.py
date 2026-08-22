from sqlalchemy.orm import Session

from src.db.models.seguimiento_model import Seguimiento


class SeguimientoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, seguidor_id: int, seguido_id: int) -> Seguimiento | None:
        return self.db.get(Seguimiento, (seguidor_id, seguido_id))

    def create(self, seguidor_id: int, seguido_id: int) -> Seguimiento:
        seguimiento = Seguimiento(seguidor_id=seguidor_id, seguido_id=seguido_id)
        self.db.add(seguimiento)
        self.db.commit()
        self.db.refresh(seguimiento)
        return seguimiento

    def delete(self, seguimiento: Seguimiento) -> None:
        self.db.delete(seguimiento)
        self.db.commit()

    def get_followed_ids(self, seguidor_id: int) -> set[int]:
        return {
            seguido_id
            for (seguido_id,) in self.db.query(Seguimiento.seguido_id)
            .filter(Seguimiento.seguidor_id == seguidor_id)
            .all()
        }

    def count_following(self, seguidor_id: int) -> int:
        return (
            self.db.query(Seguimiento)
            .filter(Seguimiento.seguidor_id == seguidor_id)
            .count()
        )
