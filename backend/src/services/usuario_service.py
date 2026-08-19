from sqlalchemy.orm import Session

from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import CreateUsuarioDTO, UsuarioResponseDTO
from src.mappers.usuario_mapper import UsuarioMapper
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, NotFoundError
from src.utils.hash import hash_password


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
