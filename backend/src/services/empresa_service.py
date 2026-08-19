from sqlalchemy.orm import Session

from src.dtos.empresa_dto import (
    CreateEmpresaDTO,
    EmpresaResponseDTO,
    UpdateEmpresaDTO,
)
from src.mappers.empresa_mapper import EmpresaMapper
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.db.models.empresa_usuario_model import RolEmpresa
from src.utils.errors import ForbiddenError, NotFoundError


class EmpresaService:
    def __init__(self, db: Session):
        self.repository = EmpresaRepository(db)
        self.empresa_usuario_repository = EmpresaUsuarioRepository(db)

    def create(
        self,
        empresa_data: CreateEmpresaDTO,
        usuario_actual_id: int,
    ) -> EmpresaResponseDTO:
        empresa = self.repository.create_with_owner(empresa_data, usuario_actual_id)
        return EmpresaMapper.to_response_dto(empresa)

    def get_by_id(self, empresa_id: int) -> EmpresaResponseDTO:
        empresa = self.repository.get_by_id(empresa_id)
        if empresa is None:
            raise NotFoundError("Empresa no encontrada.")

        return EmpresaMapper.to_response_dto(empresa)

    def update(
        self,
        empresa_id: int,
        empresa_data: UpdateEmpresaDTO,
        usuario_actual_id: int,
    ) -> EmpresaResponseDTO:
        empresa = self.repository.get_by_id(empresa_id)
        if empresa is None:
            raise NotFoundError("Empresa no encontrada.")

        if not self.empresa_usuario_repository.has_any_role(
            empresa_id,
            usuario_actual_id,
            (RolEmpresa.OWNER,),
        ):
            raise ForbiddenError("No tiene permisos para modificar la empresa.")

        empresa_actualizada = self.repository.update(empresa, empresa_data)
        return EmpresaMapper.to_response_dto(empresa_actualizada)
