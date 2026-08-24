from pydantic import BaseModel, ConfigDict

from src.db.models.empresa_usuario_model import RolEmpresa
from src.dtos.empresa_dto import EmpresaResponseDTO


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


class MiembroEmpresaResponseDTO(BaseModel):
    usuario_id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None
    rol: RolEmpresa


class MiEmpresaResponseDTO(BaseModel):
    empresa: EmpresaResponseDTO
    rol: RolEmpresa
