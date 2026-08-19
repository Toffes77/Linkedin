from pydantic import BaseModel, ConfigDict

from src.db.models.empresa_usuario_model import RolEmpresa


class CreateEmpresaUsuarioDTO(BaseModel):
    usuario_id: int
    rol: RolEmpresa


class UpdateEmpresaUsuarioDTO(BaseModel):
    rol: RolEmpresa


class EmpresaUsuarioResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    empresa_id: int
    usuario_id: int
    rol: RolEmpresa
