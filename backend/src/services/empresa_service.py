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
from src.utils.image_storage import (
    delete_managed_image,
    save_image,
    validate_and_get_extension,
)


class EmpresaService:
    def __init__(self, db: Session):
        self.db = db
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

    def search(self, nombre: str) -> list[EmpresaResponseDTO]:
        empresas = self.repository.search_by_name(nombre.strip())
        return [EmpresaMapper.to_response_dto(empresa) for empresa in empresas]

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

    def update_profile_photo(
        self,
        empresa_id: int,
        usuario_actual_id: int,
        filename: str | None,
        content: bytes,
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

        extension = validate_and_get_extension(filename, content)
        previous_url = empresa.foto_perfil_url
        photo_url = save_image("empresa", empresa.id, extension, content)
        try:
            empresa_actualizada = self.repository.update_profile_photo(
                empresa,
                photo_url,
                commit=False,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            delete_managed_image(photo_url, "empresa", empresa.id)
            raise

        delete_managed_image(previous_url, "empresa", empresa.id)
        return EmpresaMapper.to_response_dto(empresa_actualizada)
