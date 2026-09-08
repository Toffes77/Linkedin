from pydantic import BaseModel, ConfigDict

from src.db.models.empresa_usuario_model import RolEmpresa
from src.schemas.empresa_schema import GetEmpresaSchema


class CreateEmpresaUsuarioSchema(BaseModel):
    """Alta de un usuario como miembro; solo la puede hacer un OWNER."""

    usuario_id: int
    rol: RolEmpresa


class UpdateEmpresaUsuarioSchema(BaseModel):
    """Nuevo rol de un miembro existente."""

    rol: RolEmpresa


class GetEmpresaUsuarioSchema(BaseModel):
    """Relación empresa-usuario con su rol administrativo."""

    model_config = ConfigDict(from_attributes=True)

    empresa_id: int
    usuario_id: int
    rol: RolEmpresa


class GetMiembroEmpresaSchema(BaseModel):
    """Vista pública de un miembro de la empresa."""

    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    nombre: str
    headline: str
    foto_perfil_url: str | None = None
    rol: RolEmpresa


class GetMiEmpresaSchema(BaseModel):
    """Empresa a la que pertenece el usuario autenticado y su rol."""

    model_config = ConfigDict(from_attributes=True)

    empresa: GetEmpresaSchema
    rol: RolEmpresa
