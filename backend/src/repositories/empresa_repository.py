from sqlalchemy.orm import Session

from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import RolEmpresa
from src.dtos.empresa_dto import CreateEmpresaDTO, UpdateEmpresaDTO
from src.mappers.empresa_mapper import EmpresaMapper
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper


class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, empresa_data: CreateEmpresaDTO) -> Empresa:
        empresa = EmpresaMapper.to_model(empresa_data)
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
            empresa = EmpresaMapper.to_model(empresa_data)
            self.db.add(empresa)
            self.db.flush()
            self.db.add(
                EmpresaUsuarioMapper.to_model_from_values(
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

    def get_by_ids(self, empresa_ids: list[int]) -> list[Empresa]:
        if not empresa_ids:
            return []
        return self.db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all()

    def get_by_id_for_update(self, empresa_id: int) -> Empresa | None:
        return (
            self.db.query(Empresa)
            .populate_existing()
            .filter(Empresa.id == empresa_id)
            .with_for_update(of=Empresa)
            .first()
        )

    def search_by_name(self, nombre: str) -> list[Empresa]:
        return (
            self.db.query(Empresa)
            .filter(Empresa.nombre.ilike(f"%{nombre}%"))
            .order_by(Empresa.nombre)
            .all()
        )

    def update(self, empresa: Empresa, empresa_data: UpdateEmpresaDTO) -> Empresa:
        EmpresaMapper.apply_update(empresa, empresa_data)

        self.db.commit()
        self.db.refresh(empresa)
        return empresa

    def update_profile_photo(
        self,
        empresa: Empresa,
        foto_perfil_url: str,
        *,
        commit: bool = True,
    ) -> Empresa:
        empresa.foto_perfil_url = foto_perfil_url
        if commit:
            self.db.commit()
            self.db.refresh(empresa)
        else:
            self.db.flush()
        return empresa
