from sqlalchemy.orm import Session

from src.db.models.publicacion_model import Publicacion
from src.dtos.publicacion_dto import CreatePublicacionDTO, UpdatePublicacionDTO


class PublicacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, publicacion_data: CreatePublicacionDTO) -> Publicacion:
        publicacion = Publicacion(**publicacion_data.model_dump())
        self.db.add(publicacion)
        self.db.commit()
        self.db.refresh(publicacion)
        return publicacion

    def get_by_id(self, publicacion_id: int) -> Publicacion | None:
        return self.db.get(Publicacion, publicacion_id)

    def get_by_autor(self, autor_id: int) -> list[Publicacion]:
        return (
            self.db.query(Publicacion)
            .filter(Publicacion.autor_id == autor_id)
            .all()
        )

    def update(
        self,
        publicacion: Publicacion,
        publicacion_data: UpdatePublicacionDTO,
    ) -> Publicacion:
        for field, value in publicacion_data.model_dump(exclude_unset=True).items():
            setattr(publicacion, field, value)

        self.db.commit()
        self.db.refresh(publicacion)
        return publicacion

    def delete(self, publicacion: Publicacion) -> None:
        self.db.delete(publicacion)
        self.db.commit()
