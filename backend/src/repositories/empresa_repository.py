from sqlalchemy.orm import Session

from src.db.models.empresa_model import Empresa
from src.dtos.empresa_dto import CreateEmpresaDTO, UpdateEmpresaDTO


class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, empresa_data: CreateEmpresaDTO) -> Empresa:
        empresa = Empresa(**empresa_data.model_dump(mode="json"))
        self.db.add(empresa)
        self.db.commit()
        self.db.refresh(empresa)
        return empresa

    def get_by_id(self, empresa_id: int) -> Empresa | None:
        return self.db.query(Empresa).filter(Empresa.id == empresa_id).first()

    def update(self, empresa: Empresa, empresa_data: UpdateEmpresaDTO) -> Empresa:
        for field, value in empresa_data.model_dump(
            exclude_unset=True, mode="json"
        ).items():
            setattr(empresa, field, value)

        self.db.commit()
        self.db.refresh(empresa)
        return empresa
