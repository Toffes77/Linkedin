from pydantic import BaseModel, ConfigDict

from src.db.models.empresa_usuario_model import RolEmpresa
from src.schemas.empresa_schema import GetEmpresaSchema


class CreateEmpresaUsuarioSchema(BaseModel):
    usuario_id: int
    rol: RolEmpresa


class UpdateEmpresaUsuarioSchema(BaseModel):
    rol: RolEmpresa


class GetEmpresaUsuarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    empresa_id: int
    usuario_id: int
    rol: RolEmpresa


class GetMiembroEmpresaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None
    rol: RolEmpresa


class GetMiEmpresaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    empresa: GetEmpresaSchema
    rol: RolEmpresa
