from sqlalchemy.orm import Session

from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.dtos.empresa_usuario_dto import (
    CreateEmpresaUsuarioDTO,
    EmpresaUsuarioResponseDTO,
    MiEmpresaResponseDTO,
    MiembroEmpresaResponseDTO,
    UpdateEmpresaUsuarioDTO,
)
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper
from src.mappers.empresa_mapper import EmpresaMapper
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, ForbiddenError, NotFoundError


class EmpresaUsuarioService:
    def __init__(self, db: Session):
        self.repository = EmpresaUsuarioRepository(db)
        self.empresa_repository = EmpresaRepository(db)
        self.usuario_repository = UsuarioRepository(db)

    def get_by_empresa(
        self,
        empresa_id: int,
        usuario_actual_id: int,
    ) -> list[EmpresaUsuarioResponseDTO]:
        self._validar_empresa(empresa_id)
        self._requerir_owner(empresa_id, usuario_actual_id)
        relaciones = self.repository.get_by_empresa(empresa_id)
        return [EmpresaUsuarioMapper.to_response_dto(relacion) for relacion in relaciones]

    def get_by_current_user(self, usuario_id: int) -> list[MiEmpresaResponseDTO]:
        relaciones = self.repository.get_by_usuario(usuario_id)
        return [
            MiEmpresaResponseDTO(
                empresa=EmpresaMapper.to_response_dto(relacion.empresa),
                rol=relacion.rol,
            )
            for relacion in relaciones
        ]

    def get_public_members(self, empresa_id: int) -> list[MiembroEmpresaResponseDTO]:
        self._validar_empresa(empresa_id)
        relaciones = self.repository.get_public_members(empresa_id)
        return [
            EmpresaUsuarioMapper.to_member_response_dto(relacion)
            for relacion in relaciones
        ]

    def create(
        self,
        empresa_id: int,
        empresa_usuario_data: CreateEmpresaUsuarioDTO,
        usuario_actual_id: int,
    ) -> EmpresaUsuarioResponseDTO:
        self._validar_empresa(empresa_id)
        self._requerir_owner(empresa_id, usuario_actual_id)

        if self.usuario_repository.get_by_id(empresa_usuario_data.usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

        if (
            self.repository.get_by_empresa_and_usuario(
                empresa_id,
                empresa_usuario_data.usuario_id,
            )
            is not None
        ):
            raise ConflictError("El usuario ya pertenece a la empresa.")

        relacion = EmpresaUsuarioMapper.to_model(empresa_id, empresa_usuario_data)
        relacion_creada = self.repository.create(relacion)
        return EmpresaUsuarioMapper.to_response_dto(relacion_creada)

    def update(
        self,
        empresa_id: int,
        usuario_id: int,
        empresa_usuario_data: UpdateEmpresaUsuarioDTO,
        usuario_actual_id: int,
    ) -> EmpresaUsuarioResponseDTO:
        self._validar_empresa(empresa_id)
        self._requerir_owner(empresa_id, usuario_actual_id)
        relacion = self._obtener_relacion(empresa_id, usuario_id)

        if (
            relacion.rol == RolEmpresa.OWNER
            and empresa_usuario_data.rol != RolEmpresa.OWNER
            and self.repository.count_owners(empresa_id) == 1
        ):
            raise ConflictError("La empresa debe tener al menos un OWNER.")

        relacion_actualizada = self.repository.update(
            relacion,
            empresa_usuario_data.rol,
        )
        return EmpresaUsuarioMapper.to_response_dto(relacion_actualizada)

    def delete(
        self,
        empresa_id: int,
        usuario_id: int,
        usuario_actual_id: int,
    ) -> None:
        self._validar_empresa(empresa_id)
        self._requerir_owner(empresa_id, usuario_actual_id)
        relacion = self._obtener_relacion(empresa_id, usuario_id)

        if (
            relacion.rol == RolEmpresa.OWNER
            and self.repository.count_owners(empresa_id) == 1
        ):
            raise ConflictError("La empresa debe tener al menos un OWNER.")

        self.repository.delete(relacion)

    def _validar_empresa(self, empresa_id: int) -> None:
        if self.empresa_repository.get_by_id(empresa_id) is None:
            raise NotFoundError("Empresa no encontrada.")

    def _requerir_owner(self, empresa_id: int, usuario_id: int) -> None:
        if not self.repository.has_any_role(
            empresa_id,
            usuario_id,
            (RolEmpresa.OWNER,),
        ):
            raise ForbiddenError("No tiene permisos para administrar la empresa.")

    def _obtener_relacion(
        self,
        empresa_id: int,
        usuario_id: int,
    ) -> EmpresaUsuario:
        relacion = self.repository.get_by_empresa_and_usuario(empresa_id, usuario_id)
        if relacion is None:
            raise NotFoundError("El usuario no pertenece a la empresa.")
        return relacion
