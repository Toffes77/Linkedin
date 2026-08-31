from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.db.models.experiencia_model import Experiencia
from src.dtos.experiencia_dto import CreateExperienciaDTO, UpdateExperienciaDTO
from src.mappers.experiencia_mapper import ExperienciaMapper


class ExperienciaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, experiencia_data: CreateExperienciaDTO) -> Experiencia:
        experiencia = ExperienciaMapper.to_model(experiencia_data)
        self.db.add(experiencia)
        self.db.commit()
        self.db.refresh(experiencia)
        return experiencia

    def get_by_id(self, experiencia_id: int) -> Experiencia | None:
        return self.db.get(Experiencia, experiencia_id)

    def get_by_usuario(self, usuario_id: int) -> list[Experiencia]:
        return (
            self.db.query(Experiencia)
            .filter(Experiencia.usuario_id == usuario_id)
            .all()
        )

    def exists_overlap(
        self,
        usuario_id: int,
        empresa_id: int,
        desde: date,
        hasta: date | None,
        experiencia_id_a_excluir: int | None = None,
    ) -> bool:
        query = self.db.query(Experiencia.id).filter(
            Experiencia.usuario_id == usuario_id,
            Experiencia.empresa_id == empresa_id,
            or_(Experiencia.hasta.is_(None), Experiencia.hasta >= desde),
        )
        if hasta is not None:
            query = query.filter(Experiencia.desde <= hasta)
        if experiencia_id_a_excluir is not None:
            query = query.filter(Experiencia.id != experiencia_id_a_excluir)
        return query.first() is not None

    def lock_overlap_scope(self, usuario_id: int, empresa_id: int) -> None:
        if self.db.bind is None or self.db.bind.dialect.name != "postgresql":
            return
        lock_key = (usuario_id << 32) | empresa_id
        self.db.execute(select(func.pg_advisory_xact_lock(lock_key)))

    def update(
        self,
        experiencia: Experiencia,
        experiencia_data: UpdateExperienciaDTO,
    ) -> Experiencia:
        ExperienciaMapper.apply_update(experiencia, experiencia_data)

        self.db.commit()
        self.db.refresh(experiencia)
        return experiencia

    def delete(self, experiencia: Experiencia) -> None:
        self.db.delete(experiencia)
        self.db.commit()
