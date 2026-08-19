from sqlalchemy.orm import Session

from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import (
    CreateUsuarioDTO,
    PasswordUpdateResponseDTO,
    UpdatePasswordDTO,
    UpdateUsuarioDTO,
    UsuarioResponseDTO,
)
from src.mappers.usuario_mapper import UsuarioMapper
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import BadRequestError, ConflictError, NotFoundError, UnauthorizedError
from src.utils.hash import hash_password, verify_password
from src.utils.image_storage import (
    delete_managed_image,
    save_image,
    validate_and_get_extension,
)


class UsuarioService:
    def __init__(self, db: Session):
        self.repository = UsuarioRepository(db)

    def create(self, usuario_data: CreateUsuarioDTO) -> UsuarioResponseDTO:
        if self.repository.get_by_email(usuario_data.email) is not None:
            raise ConflictError("El email ya se encuentra registrado.")

        usuario = UsuarioMapper.to_model(
            usuario_data,
            password_hash=hash_password(usuario_data.password),
        )
        usuario_creado = self.repository.create(usuario)
        return UsuarioMapper.to_response_dto(usuario_creado)

    def get_by_id(self, usuario_id: int) -> UsuarioResponseDTO:
        usuario = self.repository.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")

        return UsuarioMapper.to_response_dto(usuario)

    def get_by_email(self, email: str) -> Usuario | None:
        return self.repository.get_by_email(email)

    def search(
        self,
        texto: str,
        ciudad: str | None = None,
    ) -> list[UsuarioResponseDTO]:
        usuarios = self.repository.search(texto, ciudad)
        return [UsuarioMapper.to_response_dto(usuario) for usuario in usuarios]

    def update_profile(
        self,
        usuario_actual_id: int,
        usuario_data: UpdateUsuarioDTO,
    ) -> UsuarioResponseDTO:
        usuario = self.repository.get_by_id(usuario_actual_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")

        usuario_actualizado = self.repository.update_profile(usuario, usuario_data)
        return UsuarioMapper.to_response_dto(usuario_actualizado)

    def update_profile_photo(
        self,
        usuario_id: int,
        filename: str | None,
        content: bytes,
    ) -> UsuarioResponseDTO:
        usuario = self.repository.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")

        extension = validate_and_get_extension(filename, content)
        previous_url = usuario.foto_perfil_url
        photo_url = save_image("usuario", usuario.id, extension, content)
        try:
            usuario_actualizado = self.repository.update_profile_photo(usuario, photo_url)
        except Exception:
            if photo_url != previous_url:
                delete_managed_image(photo_url, "usuario", usuario.id)
            raise

        if previous_url != photo_url:
            delete_managed_image(previous_url, "usuario", usuario.id)
        return UsuarioMapper.to_response_dto(usuario_actualizado)

    def update_password(
        self,
        usuario_actual_id: int,
        password_data: UpdatePasswordDTO,
    ) -> PasswordUpdateResponseDTO:
        usuario = self.repository.get_by_id(usuario_actual_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")

        if not verify_password(password_data.password_actual, usuario.password_hash):
            raise UnauthorizedError("La contrase\u00f1a actual es incorrecta.")

        if password_data.password_nueva == password_data.password_actual:
            raise BadRequestError("La nueva contrase\u00f1a debe ser diferente a la actual.")

        self.repository.update_password_hash(
            usuario,
            hash_password(password_data.password_nueva),
        )
        return PasswordUpdateResponseDTO(
            message="Contrase\u00f1a actualizada correctamente"
        )
