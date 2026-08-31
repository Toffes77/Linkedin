from sqlalchemy.orm import Session

from src.db.models.empresa_usuario_model import RolEmpresa
from src.dtos.postulacion_dto import (
    CreatePostulacionDTO,
    PostulacionResponseDTO,
    UpdatePostulacionDTO,
)
from src.dtos.notificacion_dto import CreateNotificacionDTO
from src.dtos.oferta_dto import UpdateOfertaDTO
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper
from src.mappers.postulacion_mapper import PostulacionMapper
from src.repositories.oferta_repository import OfertaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.repositories.postulacion_repository import PostulacionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.services.notificacion_service import NotificacionService
from src.utils.errors import ConflictError, ForbiddenError, NotFoundError


class PostulacionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PostulacionRepository(db)
        self.oferta_repository = OfertaRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.empresa_usuario_repository = EmpresaUsuarioRepository(db)
        self.notificacion_service = NotificacionService(db)

    def create(
        self,
        postulacion_data: CreatePostulacionDTO,
    ) -> PostulacionResponseDTO:
        postulante = self._obtener_usuario(postulacion_data.usuario_id)
        oferta = self._obtener_oferta(postulacion_data.oferta_id)

        if not oferta.publicada:
            raise ConflictError("No se puede postular a una oferta no publicada.")

        if (
            self.repository.get_by_oferta_and_usuario(
                postulacion_data.oferta_id,
                postulacion_data.usuario_id,
            )
            is not None
        ):
            raise ConflictError("El usuario ya se postuló a esta oferta.")

        try:
            postulacion = self.repository.create(postulacion_data, commit=False)
            receptores = self.empresa_usuario_repository.get_user_ids_by_empresa_and_roles(
                oferta.empresa_id,
                (RolEmpresa.OWNER, RolEmpresa.RECRUITER),
            )
            self.notificacion_service.create_many(
                [
                    CreateNotificacionDTO(
                        usuario_id=receptor_id,
                        tipo="POSTULACION_NUEVA",
                        mensaje=f'{postulante.nombre} se postuló a "{oferta.titulo}".',
                        postulacion_id=postulacion.id,
                        oferta_id=oferta.id,
                    )
                    for receptor_id in receptores
                ],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(postulacion)
        except Exception:
            self.db.rollback()
            raise
        return PostulacionMapper.to_response_dto(postulacion)

    def get_by_id(
        self,
        postulacion_id: int,
        usuario_actual_id: int,
    ) -> PostulacionResponseDTO:
        postulacion = self.repository.get_by_id(postulacion_id)
        if postulacion is None:
            raise NotFoundError("Postulación no encontrada.")

        self._requerir_acceso_postulacion(postulacion, usuario_actual_id)
        return PostulacionMapper.to_response_dto(postulacion)

    def get_by_oferta(
        self,
        oferta_id: int,
        usuario_actual_id: int,
    ) -> list[PostulacionResponseDTO]:
        oferta = self._obtener_oferta(oferta_id)
        self._requerir_gestor_empresa(oferta.empresa_id, usuario_actual_id)
        postulaciones = self.repository.get_by_oferta(oferta_id)
        return [PostulacionMapper.to_response_dto(postulacion) for postulacion in postulaciones]

    def get_by_usuario(
        self,
        usuario_id: int,
        usuario_actual_id: int,
    ) -> list[PostulacionResponseDTO]:
        if usuario_id != usuario_actual_id:
            raise ForbiddenError("No puede consultar postulaciones de otro usuario.")

        self._validar_usuario(usuario_id)
        postulaciones = self.repository.get_by_usuario(usuario_id)
        return [PostulacionMapper.to_response_dto(postulacion) for postulacion in postulaciones]

    def update(
        self,
        postulacion_id: int,
        postulacion_data: UpdatePostulacionDTO,
        usuario_actual_id: int,
    ) -> PostulacionResponseDTO:
        postulacion = self.repository.get_by_id_for_update(postulacion_id)
        if postulacion is None:
            self.db.rollback()
            raise NotFoundError("Postulación no encontrada.")

        try:
            oferta = self._obtener_oferta(postulacion.oferta_id)
            self._requerir_gestor_empresa(oferta.empresa_id, usuario_actual_id)
            self._validar_transicion(postulacion.estado, postulacion_data.estado)
        except Exception:
            self.db.rollback()
            raise
        try:
            postulacion_actualizada = self.repository.update(
                postulacion,
                postulacion_data,
                commit=False,
            )
            if postulacion_actualizada.estado == "contratado":
                self._agregar_colaborador_si_no_es_miembro(
                    oferta.empresa_id,
                    postulacion_actualizada.usuario_id,
                )
                self.oferta_repository.update(
                    oferta,
                    UpdateOfertaDTO(publicada=False),
                    commit=False,
                )
            self.notificacion_service.create_many(
                [
                    CreateNotificacionDTO(
                        usuario_id=postulacion_actualizada.usuario_id,
                        tipo="POSTULACION_ESTADO",
                        mensaje=(
                            f'Tu postulación para "{oferta.titulo}" cambió a '
                            f'"{postulacion_actualizada.estado.upper()}".'
                        ),
                        postulacion_id=postulacion_actualizada.id,
                        oferta_id=oferta.id,
                    )
                ],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(postulacion_actualizada)
        except Exception:
            self.db.rollback()
            raise
        return PostulacionMapper.to_response_dto(postulacion_actualizada)

    def _agregar_colaborador_si_no_es_miembro(
        self,
        empresa_id: int,
        usuario_id: int,
    ) -> None:
        relacion = self.empresa_usuario_repository.get_by_empresa_and_usuario(
            empresa_id,
            usuario_id,
        )
        if relacion is not None:
            return

        self.empresa_usuario_repository.create(
            EmpresaUsuarioMapper.to_model_from_values(
                empresa_id=empresa_id,
                usuario_id=usuario_id,
                rol=RolEmpresa.COLLABORATOR,
            ),
            commit=False,
        )

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

    def _obtener_usuario(self, usuario_id: int):
        usuario = self.usuario_repository.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuario no encontrado.")
        return usuario

    def _obtener_oferta(self, oferta_id: int):
        oferta = self.oferta_repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        return oferta

    def _requerir_gestor_empresa(self, empresa_id: int, usuario_id: int) -> None:
        if not self.empresa_usuario_repository.has_any_role(
            empresa_id,
            usuario_id,
            (RolEmpresa.OWNER, RolEmpresa.RECRUITER),
        ):
            raise ForbiddenError("No tiene permisos para gestionar postulaciones.")

    def _requerir_acceso_postulacion(
        self,
        postulacion,
        usuario_actual_id: int,
    ) -> None:
        if postulacion.usuario_id == usuario_actual_id:
            return

        self._requerir_gestor_empresa(
            postulacion.oferta.empresa_id,
            usuario_actual_id,
        )

    @staticmethod
    def _validar_transicion(estado_actual: str, nuevo_estado: str) -> None:
        transiciones_validas = {
            "nueva": {"vista", "rechazada"},
            "vista": {"entrevista", "rechazada"},
            "entrevista": {"contratado", "rechazada"},
        }

        if nuevo_estado not in transiciones_validas.get(estado_actual, set()):
            raise ConflictError(
                "La transición de estado de la postulación no es válida."
            )
