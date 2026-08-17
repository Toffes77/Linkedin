from sqlalchemy.orm import Session

from src.dtos.empresa_dto import (
    CreateEmpresaDTO,
    EmpresaResponseDTO,
    UpdateEmpresaDTO,
)
from src.repositories.empresa_repository import EmpresaRepository
from src.utils.errors import NotFoundError


class EmpresaService:
    def __init__(self, db: Session):
        self.repository = EmpresaRepository(db)

    def create(self, empresa_data: CreateEmpresaDTO) -> EmpresaResponseDTO:
        empresa = self.repository.create(empresa_data)
        return EmpresaResponseDTO.model_validate(empresa)

    def get_by_id(self, empresa_id: int) -> EmpresaResponseDTO:
        empresa = self.repository.get_by_id(empresa_id)
        if empresa is None:
            raise NotFoundError("Empresa no encontrada.")

        return EmpresaResponseDTO.model_validate(empresa)

    def update(
        self,
        empresa_id: int,
        empresa_data: UpdateEmpresaDTO,
    ) -> EmpresaResponseDTO:
        empresa = self.repository.get_by_id(empresa_id)
        if empresa is None:
            raise NotFoundError("Empresa no encontrada.")

        empresa_actualizada = self.repository.update(empresa, empresa_data)
        return EmpresaResponseDTO.model_validate(empresa_actualizada)
