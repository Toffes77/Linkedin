from pydantic import BaseModel, ConfigDict

from src.db.models.empresa_usuario_model import RolEmpresa


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
