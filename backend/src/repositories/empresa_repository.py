from sqlalchemy.orm import Session

from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
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

    def create_with_owner(
        self,
        empresa_data: CreateEmpresaDTO,
        usuario_id: int,
    ) -> Empresa:
        try:
            empresa = Empresa(**empresa_data.model_dump(mode="json"))
            self.db.add(empresa)
            self.db.flush()
            self.db.add(
                EmpresaUsuario(
                    empresa_id=empresa.id,
                    usuario_id=usuario_id,
                    rol=RolEmpresa.OWNER,
                )
            )
            self.db.commit()
            self.db.refresh(empresa)
            return empresa
        except Exception:
            self.db.rollback()
            raise

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
