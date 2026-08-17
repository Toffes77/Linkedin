from sqlalchemy.orm import Session

from src.db.models.experiencia_model import Experiencia
from src.dtos.experiencia_dto import CreateExperienciaDTO, UpdateExperienciaDTO


class ExperienciaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, experiencia_data: CreateExperienciaDTO) -> Experiencia:
        experiencia = Experiencia(**experiencia_data.model_dump())
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

    def update(
        self,
        experiencia: Experiencia,
        experiencia_data: UpdateExperienciaDTO,
    ) -> Experiencia:
        for field, value in experiencia_data.model_dump(exclude_unset=True).items():
            setattr(experiencia, field, value)

        self.db.commit()
        self.db.refresh(experiencia)
        return experiencia

    def delete(self, experiencia: Experiencia) -> None:
        self.db.delete(experiencia)
        self.db.commit()
