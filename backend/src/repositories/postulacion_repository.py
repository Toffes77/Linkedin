from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models.postulacion_model import Postulacion
from src.dtos.postulacion_dto import CreatePostulacionDTO, UpdatePostulacionDTO


class PostulacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, postulacion_data: CreatePostulacionDTO) -> Postulacion:
        postulacion = Postulacion(**postulacion_data.model_dump())
        self.db.add(postulacion)
        self.db.commit()
        self.db.refresh(postulacion)
        return postulacion

    def get_by_id(self, postulacion_id: int) -> Postulacion | None:
        return self.db.get(Postulacion, postulacion_id)

    def get_by_oferta(self, oferta_id: int) -> list[Postulacion]:
        return (
            self.db.query(Postulacion)
            .filter(Postulacion.oferta_id == oferta_id)
            .all()
        )

    def get_by_usuario(self, usuario_id: int) -> list[Postulacion]:
        return (
            self.db.query(Postulacion)
            .filter(Postulacion.usuario_id == usuario_id)
            .all()
        )

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
    ) -> Postulacion:
        for field, value in postulacion_data.model_dump(exclude_unset=True).items():
            setattr(postulacion, field, value)

        self.db.commit()
        self.db.refresh(postulacion)
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
