from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

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

    def get_all_by_publicacion(self, publicacion_id: int) -> list[Comentario]:
        return (
            self.db.query(Comentario)
            .options(joinedload(Comentario.autor))
            .filter(Comentario.publicacion_id == publicacion_id)
            .order_by(Comentario.fecha.asc(), Comentario.id.asc())
            .all()
        )

    def count_by_publicacion(self, publicacion_id: int) -> int:
        return (
            self.db.query(func.count(Comentario.id))
            .filter(Comentario.publicacion_id == publicacion_id)
            .scalar()
            or 0
        )

    def delete(self, comentario: Comentario) -> None:
        self.db.delete(comentario)
        self.db.commit()
