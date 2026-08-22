from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.dtos.empresa_usuario_dto import (
    CreateEmpresaUsuarioDTO,
    EmpresaUsuarioResponseDTO,
    UpdateEmpresaUsuarioDTO,
)
from src.schemas.empresa_usuario_schema import (
    CreateEmpresaUsuarioSchema,
    GetEmpresaUsuarioSchema,
    GetMiEmpresaSchema,
    UpdateEmpresaUsuarioSchema,
)
from src.dtos.empresa_usuario_dto import MiEmpresaResponseDTO


class EmpresaUsuarioMapper:
    @staticmethod
    def to_create_dto(schema: CreateEmpresaUsuarioSchema) -> CreateEmpresaUsuarioDTO:
        return CreateEmpresaUsuarioDTO(**schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdateEmpresaUsuarioSchema) -> UpdateEmpresaUsuarioDTO:
        return UpdateEmpresaUsuarioDTO(**schema.model_dump())

    @staticmethod
    def to_model(
        empresa_id: int,
        data: CreateEmpresaUsuarioDTO,
    ) -> EmpresaUsuario:
        return EmpresaUsuario(
            empresa_id=empresa_id,
            usuario_id=data.usuario_id,
            rol=data.rol,
        )

    @staticmethod
    def to_model_from_values(
        empresa_id: int,
        usuario_id: int,
        rol: RolEmpresa,
    ) -> EmpresaUsuario:
        return EmpresaUsuario(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            rol=rol,
        )

    @staticmethod
    def to_response_dto(model: EmpresaUsuario) -> EmpresaUsuarioResponseDTO:
        return EmpresaUsuarioResponseDTO.model_validate(model)

    @staticmethod
    def to_response_schema(dto: EmpresaUsuarioResponseDTO) -> GetEmpresaUsuarioSchema:
        return GetEmpresaUsuarioSchema.model_validate(dto)

    @staticmethod
    def to_my_company_response_schema(dto: MiEmpresaResponseDTO) -> GetMiEmpresaSchema:
        return GetMiEmpresaSchema.model_validate(dto)
