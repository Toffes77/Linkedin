from sqlalchemy.orm import Session

from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    CreateConexionDTO,
    EstadoConexionResponseDTO,
    InvitacionRecibidaResponseDTO,
    ResumenRedResponseDTO,
    UpdateConexionDTO,
)
from src.dtos.notificacion_dto import CreateNotificacionDTO
from src.dtos.usuario_dto import UsuarioResponseDTO
from src.mappers.conexion_mapper import ConexionMapper
from src.mappers.usuario_mapper import UsuarioMapper
from src.repositories.conexion_repository import ConexionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.repositories.seguimiento_repository import SeguimientoRepository
from src.services.notificacion_service import NotificacionService
from src.utils.errors import ConflictError, ForbiddenError, NotFoundError


class ConexionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ConexionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.seguimiento_repository = SeguimientoRepository(db)
        self.notificacion_service = NotificacionService(db)

    def get_resumen_red(self, usuario_id: int) -> ResumenRedResponseDTO:
        return ResumenRedResponseDTO(
            invitaciones_enviadas=self.repository.count_pending_sent(usuario_id),
            contactos=self.repository.count_accepted_by_user(usuario_id),
            siguiendo=self.seguimiento_repository.count_following(usuario_id),
        )

    def get_invitaciones_recibidas(
        self, usuario_id: int
    ) -> list[InvitacionRecibidaResponseDTO]:
        return [
            ConexionMapper.to_invitacion_response_dto(conexion)
            for conexion in self.repository.get_pending_received_by_user(usuario_id)
        ]

    def create(
        self,
        conexion_data: CreateConexionDTO,
        usuario_autenticado_id: int,
    ) -> ConexionResponseDTO:
        if conexion_data.usuario_a != usuario_autenticado_id:
            raise ForbiddenError(
                "No se puede solicitar una conexión en nombre de otro usuario."
            )

        usuario_origen = self._obtener_usuario(conexion_data.usuario_a)
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

        try:
            conexion = self.repository.create(conexion_data, commit=False)
            self.notificacion_service.create_many(
                [
                    CreateNotificacionDTO(
                        usuario_id=conexion_data.usuario_b,
                        tipo="NUEVA_INVITACION_CONEXION",
                        mensaje=f"{usuario_origen.nombre} quiere conectar con vos.",
                        usuario_origen_id=conexion_data.usuario_a,
                    )
                ],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(conexion)
        except Exception:
            self.db.rollback()
            raise
        return ConexionMapper.to_response_dto(conexion)

    def get_estado(
        self,
        usuario_autenticado_id: int,
        otro_usuario_id: int,
    ) -> EstadoConexionResponseDTO:
        self._validar_usuario(otro_usuario_id)
        conexion = self.repository.get_by_usuarios(
            usuario_autenticado_id,
            otro_usuario_id,
        )
        if conexion is None:
            return EstadoConexionResponseDTO(estado="SIN_CONEXION")

        if conexion.estado == "aceptada":
            estado = "CONECTADO"
        elif conexion.estado == "rechazada":
            estado = "RECHAZADA"
        elif conexion.usuario_a == usuario_autenticado_id:
            estado = "PENDIENTE_ENVIADA"
        else:
            estado = "PENDIENTE_RECIBIDA"

        return EstadoConexionResponseDTO(
            estado=estado,
            usuario_a=conexion.usuario_a,
            usuario_b=conexion.usuario_b,
        )

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

        if conexion_data.estado == "rechazada":
            conexion_actualizada = self.repository.update(conexion, conexion_data)
            return ConexionMapper.to_response_dto(conexion_actualizada)

        usuario_origen = self._obtener_usuario(usuario_autenticado_id)
        try:
            conexion_actualizada = self.repository.update(
                conexion,
                conexion_data,
                commit=False,
            )
            self.notificacion_service.create_many(
                [
                    CreateNotificacionDTO(
                        usuario_id=conexion.usuario_a,
                        tipo="CONEXION_ACEPTADA",
                        mensaje=(
                            f"{usuario_origen.nombre} aceptó tu solicitud de conexión."
                        ),
                        usuario_origen_id=conexion.usuario_b,
                    )
                ],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(conexion_actualizada)
        except Exception:
            self.db.rollback()
            raise
        return ConexionMapper.to_response_dto(conexion_actualizada)

    def _validar_usuario(self, usuario_id: int) -> None:
        self._obtener_usuario(usuario_id)

    def _obtener_usuario(self, usuario_id: int):
        usuario = self.usuario_repository.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        return usuario
