from sqlalchemy.orm import Session

from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    CreateConexionDTO,
    UpdateConexionDTO,
)
from src.dtos.usuario_dto import UsuarioResponseDTO
from src.mappers.conexion_mapper import ConexionMapper
from src.mappers.usuario_mapper import UsuarioMapper
from src.repositories.conexion_repository import ConexionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, ForbiddenError, NotFoundError


class ConexionService:
    def __init__(self, db: Session):
        self.repository = ConexionRepository(db)
        self.usuario_repository = UsuarioRepository(db)

    def create(
        self,
        conexion_data: CreateConexionDTO,
        usuario_autenticado_id: int,
    ) -> ConexionResponseDTO:
        if conexion_data.usuario_a != usuario_autenticado_id:
            raise ForbiddenError(
                "No se puede solicitar una conexión en nombre de otro usuario."
            )

        self._validar_usuario(conexion_data.usuario_a)
        self._validar_usuario(conexion_data.usuario_b)

        if conexion_data.usuario_a == conexion_data.usuario_b:
            raise ConflictError("No se puede solicitar una conexión consigo mismo.")

        if (
            self.repository.get_by_usuarios(
                conexion_data.usuario_a,
                conexion_data.usuario_b,
            )
            is not None
        ):
            raise ConflictError("Ya existe una conexión entre los usuarios.")

        conexion = self.repository.create(conexion_data)
        return ConexionMapper.to_response_dto(conexion)

    def get_by_id(
        self,
        usuario_a: int,
        usuario_b: int,
    ) -> ConexionResponseDTO:
        conexion = self.repository.get_by_id(usuario_a, usuario_b)
        if conexion is None:
            raise NotFoundError("Conexión no encontrada.")

        return ConexionMapper.to_response_dto(conexion)

    def get_by_usuario(self, usuario_id: int) -> list[ConexionResponseDTO]:
        self._validar_usuario(usuario_id)
        conexiones = self.repository.get_by_usuario(usuario_id)
        return [ConexionMapper.to_response_dto(conexion) for conexion in conexiones]

    def get_second_degree_suggestions(
        self,
        usuario_id: int,
    ) -> list[UsuarioResponseDTO]:
        self._validar_usuario(usuario_id)
        usuarios = self.repository.get_second_degree_suggestions(usuario_id)
        return [
            UsuarioMapper.to_response_dto(usuario)
            for usuario in usuarios
        ]

    def update(
        self,
        usuario_a: int,
        usuario_b: int,
        conexion_data: UpdateConexionDTO,
        usuario_autenticado_id: int,
    ) -> ConexionResponseDTO:
        conexion = self.repository.get_by_id(usuario_a, usuario_b)
        if conexion is None:
            raise NotFoundError("Conexión no encontrada.")

        if conexion.estado != "pendiente":
            raise ConflictError("Solo se pueden modificar conexiones pendientes.")

        if conexion.usuario_b != usuario_autenticado_id:
            raise ForbiddenError(
                "Solo el destinatario puede responder la solicitud de conexión."
            )

        if conexion_data.estado not in ("aceptada", "rechazada"):
            raise ConflictError("La conexión debe aceptarse o rechazarse.")

        conexion_actualizada = self.repository.update(conexion, conexion_data)
        return ConexionMapper.to_response_dto(conexion_actualizada)

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")
