from sqlalchemy.orm import Session

from src.dtos.postulacion_dto import (
    CreatePostulacionDTO,
    PostulacionResponseDTO,
    UpdatePostulacionDTO,
)
from src.repositories.oferta_repository import OfertaRepository
from src.repositories.postulacion_repository import PostulacionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, NotFoundError


class PostulacionService:
    def __init__(self, db: Session):
        self.repository = PostulacionRepository(db)
        self.oferta_repository = OfertaRepository(db)
        self.usuario_repository = UsuarioRepository(db)

    def create(
        self,
        postulacion_data: CreatePostulacionDTO,
    ) -> PostulacionResponseDTO:
        self._validar_usuario(postulacion_data.usuario_id)
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

        postulacion = self.repository.create(postulacion_data)
        return PostulacionResponseDTO.model_validate(postulacion)

    def get_by_id(self, postulacion_id: int) -> PostulacionResponseDTO:
        postulacion = self.repository.get_by_id(postulacion_id)
        if postulacion is None:
            raise NotFoundError("Postulación no encontrada.")

        return PostulacionResponseDTO.model_validate(postulacion)

    def get_by_oferta(self, oferta_id: int) -> list[PostulacionResponseDTO]:
        self._obtener_oferta(oferta_id)
        postulaciones = self.repository.get_by_oferta(oferta_id)
        return [
            PostulacionResponseDTO.model_validate(postulacion)
            for postulacion in postulaciones
        ]

    def get_by_usuario(self, usuario_id: int) -> list[PostulacionResponseDTO]:
        self._validar_usuario(usuario_id)
        postulaciones = self.repository.get_by_usuario(usuario_id)
        return [
            PostulacionResponseDTO.model_validate(postulacion)
            for postulacion in postulaciones
        ]

    def update(
        self,
        postulacion_id: int,
        postulacion_data: UpdatePostulacionDTO,
    ) -> PostulacionResponseDTO:
        postulacion = self.repository.get_by_id(postulacion_id)
        if postulacion is None:
            raise NotFoundError("Postulación no encontrada.")

        self._validar_transicion(postulacion.estado, postulacion_data.estado)
        postulacion_actualizada = self.repository.update(
            postulacion,
            postulacion_data,
        )
        return PostulacionResponseDTO.model_validate(postulacion_actualizada)

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

    def _obtener_oferta(self, oferta_id: int):
        oferta = self.oferta_repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        return oferta

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
