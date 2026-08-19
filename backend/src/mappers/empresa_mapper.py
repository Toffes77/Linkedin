from src.db.models.empresa_model import Empresa
from src.dtos.empresa_dto import CreateEmpresaDTO, EmpresaResponseDTO, UpdateEmpresaDTO
from src.schemas.empresa_schema import (
    CreateEmpresaSchema,
    GetEmpresaSchema,
    UpdateEmpresaSchema,
)


class EmpresaMapper:
    @staticmethod
    def to_create_dto(schema: CreateEmpresaSchema) -> CreateEmpresaDTO:
        return CreateEmpresaDTO(**schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdateEmpresaSchema) -> UpdateEmpresaDTO:
        return UpdateEmpresaDTO(**schema.model_dump(exclude_unset=True))

    @staticmethod
    def to_model(data: CreateEmpresaDTO) -> Empresa:
        return Empresa(**data.model_dump(mode="json"))

    @staticmethod
    def apply_update(model: Empresa, data: UpdateEmpresaDTO) -> Empresa:
        for field, value in data.model_dump(exclude_unset=True, mode="json").items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(empresa: Empresa) -> EmpresaResponseDTO:
        return EmpresaResponseDTO.model_validate(empresa)

    @staticmethod
    def to_response_schema(dto: EmpresaResponseDTO) -> GetEmpresaSchema:
        return GetEmpresaSchema.model_validate(dto)
