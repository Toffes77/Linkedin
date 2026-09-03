from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session

from src.db.models.reaciones_model import Reacciones
from src.dtos.reacciones_dto import CreateReaccionDTO, UpdateReaccionDTO
from src.mappers.reaccion_mapper import ReaccionMapper


class ReaccionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, reaccion_data: CreateReaccionDTO) -> Reacciones:
        reaccion = ReaccionMapper.to_model(reaccion_data)
        self.db.add(reaccion)
        self.db.commit()
        self.db.refresh(reaccion)
        return reaccion

    def get_by_usuario_and_publicacion(
        self,
        usuario_id: int,
        publicacion_id: int,
    ) -> Reacciones | None:
        return self.db.get(Reacciones, (usuario_id, publicacion_id))

    def get_by_publicacion(self, publicacion_id: int) -> list[Reacciones]:
        return (
            self.db.query(Reacciones)
            .filter(Reacciones.publicacion_id == publicacion_id)
            .all()
        )

    def summarize_by_publicaciones(
        self,
        publicacion_ids: list[int],
        usuario_id: int | None,
    ) -> list[tuple[int, str, int, int]]:
        if not publicacion_ids:
            return []
        is_current_user = (
            case((Reacciones.usuario_id == usuario_id, 1), else_=0)
            if usuario_id is not None
            else literal(0)
        )
        return (
            self.db.query(
                Reacciones.publicacion_id,
                Reacciones.tipo,
                func.count().label("cantidad"),
                func.max(is_current_user).label("es_reaccion_actual"),
            )
            .filter(Reacciones.publicacion_id.in_(publicacion_ids))
            .group_by(Reacciones.publicacion_id, Reacciones.tipo)
            .all()
        )

    def update(
        self,
        reaccion: Reacciones,
        reaccion_data: UpdateReaccionDTO,
    ) -> Reacciones:
        ReaccionMapper.apply_update(reaccion, reaccion_data)

        self.db.commit()
        self.db.refresh(reaccion)
        return reaccion

    def delete(self, reaccion: Reacciones) -> None:
        self.db.delete(reaccion)
        self.db.commit()
