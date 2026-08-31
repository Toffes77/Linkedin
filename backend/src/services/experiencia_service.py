from datetime import date

from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from src.dtos.experiencia_dto import (
    CreateExperienciaDTO,
    ExperienciaResponseDTO,
    UpdateExperienciaDTO,
)
from src.mappers.experiencia_mapper import ExperienciaMapper
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.experiencia_repository import ExperienciaRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import ConflictError, ForbiddenError, NotFoundError


class ExperienciaService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ExperienciaRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.empresa_repository = EmpresaRepository(db)

    def create(
        self,
        experiencia_data: CreateExperienciaDTO,
        usuario_actual_id: int,
    ) -> ExperienciaResponseDTO:
        self._requerir_propietario(
            experiencia_data.usuario_id,
            usuario_actual_id,
        )
        self._validar_usuario(experiencia_data.usuario_id)
        self._validar_empresa(experiencia_data.empresa_id)
        self._validar_fechas(experiencia_data.desde, experiencia_data.hasta)
        self.repository.lock_overlap_scope(
            experiencia_data.usuario_id,
            experiencia_data.empresa_id,
        )
        self._validar_sin_solapamientos(
            experiencia_data.usuario_id,
            experiencia_data.empresa_id,
            experiencia_data.desde,
            experiencia_data.hasta,
        )

        try:
            experiencia = self.repository.create(experiencia_data)
        except (IntegrityError, OperationalError) as exc:
            self.db.rollback()
            if self._es_conflicto_solapamiento(exc) or self._es_deadlock(exc):
                raise ConflictError(
                    "El período se solapa con otra experiencia del usuario en la misma empresa."
                ) from exc
            raise
        return ExperienciaMapper.to_response_dto(experiencia)

    def get_by_id(self, experiencia_id: int) -> ExperienciaResponseDTO:
        experiencia = self.repository.get_by_id(experiencia_id)
        if experiencia is None:
            raise NotFoundError("Experiencia no encontrada.")

        return ExperienciaMapper.to_response_dto(experiencia)

    def get_by_usuario(self, usuario_id: int) -> list[ExperienciaResponseDTO]:
        self._validar_usuario(usuario_id)
        experiencias = self.repository.get_by_usuario(usuario_id)
        return [ExperienciaMapper.to_response_dto(experiencia) for experiencia in experiencias]

    def update(
        self,
        experiencia_id: int,
        experiencia_data: UpdateExperienciaDTO,
        usuario_actual_id: int,
    ) -> ExperienciaResponseDTO:
        experiencia = self.repository.get_by_id(experiencia_id)
        if experiencia is None:
            raise NotFoundError("Experiencia no encontrada.")

        self._requerir_propietario(experiencia.usuario_id, usuario_actual_id)

        fields_set = experiencia_data.model_fields_set
        if "empresa_id" in fields_set:
            if experiencia_data.empresa_id is None:
                raise ValueError("La empresa es obligatoria.")
            self._validar_empresa(experiencia_data.empresa_id)

        if "desde" in fields_set and experiencia_data.desde is None:
            raise ValueError("La fecha de inicio es obligatoria.")

        desde = (
            experiencia_data.desde
            if "desde" in fields_set
            else experiencia.desde
        )
        hasta = (
            experiencia_data.hasta
            if "hasta" in fields_set
            else experiencia.hasta
        )
        empresa_id = (
            experiencia_data.empresa_id
            if "empresa_id" in fields_set
            else experiencia.empresa_id
        )
        self._validar_fechas(desde, hasta)
        self.repository.lock_overlap_scope(experiencia.usuario_id, empresa_id)
        self._validar_sin_solapamientos(
            experiencia.usuario_id,
            empresa_id,
            desde,
            hasta,
            experiencia.id,
        )

        try:
            experiencia_actualizada = self.repository.update(
                experiencia,
                experiencia_data,
            )
        except (IntegrityError, OperationalError) as exc:
            self.db.rollback()
            if self._es_conflicto_solapamiento(exc) or self._es_deadlock(exc):
                raise ConflictError(
                    "El período se solapa con otra experiencia del usuario en la misma empresa."
                ) from exc
            raise
        return ExperienciaMapper.to_response_dto(experiencia_actualizada)

    def delete(self, experiencia_id: int, usuario_actual_id: int) -> None:
        experiencia = self.repository.get_by_id(experiencia_id)
        if experiencia is None:
            raise NotFoundError("Experiencia no encontrada.")

        self._requerir_propietario(experiencia.usuario_id, usuario_actual_id)
        self.repository.delete(experiencia)

    @staticmethod
    def _requerir_propietario(usuario_id: int, usuario_actual_id: int) -> None:
        if usuario_id != usuario_actual_id:
            raise ForbiddenError(
                "No puede modificar experiencias de otro usuario."
            )

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

    def _validar_empresa(self, empresa_id: int) -> None:
        if self.empresa_repository.get_by_id(empresa_id) is None:
            raise NotFoundError("Empresa no encontrada.")

    def _validar_fechas(self, desde: date, hasta: date | None) -> None:
        if hasta is not None and desde > hasta:
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de finalización."
            )

    def _validar_sin_solapamientos(
        self,
        usuario_id: int,
        empresa_id: int,
        desde: date,
        hasta: date | None,
        experiencia_id_a_excluir: int | None = None,
    ) -> None:
        if self.repository.exists_overlap(
            usuario_id,
            empresa_id,
            desde,
            hasta,
            experiencia_id_a_excluir,
        ):
            raise ConflictError(
                "El período se solapa con otra experiencia del usuario en la misma empresa."
            )

    @staticmethod
    def _es_conflicto_solapamiento(error: DBAPIError) -> bool:
        diagnostic = getattr(error.orig, "diag", None)
        return (
            getattr(diagnostic, "constraint_name", None)
            == "exclude_experiencia_usuario_empresa_periodo"
        )

    @staticmethod
    def _es_deadlock(error: DBAPIError) -> bool:
        return getattr(error.orig, "pgcode", None) == "40P01"
