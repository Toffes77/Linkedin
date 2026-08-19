from datetime import datetime

from sqlalchemy.orm import Session

from src.dtos.oferta_dto import (
    CreateOfertaDTO,
    OfertaEstadisticasDTO,
    OfertaResponseDTO,
    UpdateOfertaDTO,
)
from src.mappers.oferta_mapper import OfertaMapper
from src.db.models.empresa_usuario_model import RolEmpresa
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.repositories.oferta_repository import OfertaRepository
from src.repositories.postulacion_repository import PostulacionRepository
from src.utils.errors import ForbiddenError, NotFoundError


class OfertaService:
    def __init__(self, db: Session):
        self.repository = OfertaRepository(db)
        self.empresa_repository = EmpresaRepository(db)
        self.empresa_usuario_repository = EmpresaUsuarioRepository(db)
        self.postulacion_repository = PostulacionRepository(db)

    def create(
        self,
        oferta_data: CreateOfertaDTO,
        usuario_actual_id: int,
    ) -> OfertaResponseDTO:
        self._validar_empresa(oferta_data.empresa_id)
        self._requerir_gestor_empresa(oferta_data.empresa_id, usuario_actual_id)

        oferta = self.repository.create(oferta_data)
        if oferta.publicada:
            oferta.fecha_publicacion = datetime.now()
            oferta = self.repository.update(oferta, UpdateOfertaDTO())

        return OfertaMapper.to_response_dto(oferta)

    def get_by_id(self, oferta_id: int) -> OfertaResponseDTO:
        oferta = self.repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        return OfertaMapper.to_response_dto(oferta)

    def get_by_empresa(self, empresa_id: int) -> list[OfertaResponseDTO]:
        self._validar_empresa(empresa_id)
        ofertas = self.repository.get_by_empresa(empresa_id)
        return [OfertaMapper.to_response_dto(oferta) for oferta in ofertas]

    def get_publicadas(self) -> list[OfertaResponseDTO]:
        ofertas = self.repository.get_publicadas()
        return [OfertaMapper.to_response_dto(oferta) for oferta in ofertas]

    def update(
        self,
        oferta_id: int,
        oferta_data: UpdateOfertaDTO,
        usuario_actual_id: int,
    ) -> OfertaResponseDTO:
        oferta = self.repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        self._requerir_gestor_empresa(oferta.empresa_id, usuario_actual_id)

        if (
            not oferta.publicada
            and "publicada" in oferta_data.model_fields_set
            and oferta_data.publicada is True
        ):
            oferta.fecha_publicacion = datetime.now()

        oferta_actualizada = self.repository.update(oferta, oferta_data)
        return OfertaMapper.to_response_dto(oferta_actualizada)

    def get_estadisticas(
        self,
        oferta_id: int,
        usuario_actual_id: int,
    ) -> OfertaEstadisticasDTO:
        oferta = self.repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        self._requerir_gestor_empresa(oferta.empresa_id, usuario_actual_id)
        conteos = {
            "nueva": 0,
            "vista": 0,
            "entrevista": 0,
            "contratado": 0,
            "rechazada": 0,
        }
        for estado, cantidad in self.postulacion_repository.count_grouped_by_estado(
            oferta_id
        ):
            conteos[estado] = cantidad

        dias_desde_publicacion = None
        if oferta.fecha_publicacion is not None:
            dias_desde_publicacion = (datetime.now() - oferta.fecha_publicacion).days

        return OfertaEstadisticasDTO(
            oferta_id=oferta.id,
            total_postulaciones=sum(conteos.values()),
            postulaciones_por_estado=conteos,
            dias_desde_publicacion=dias_desde_publicacion,
        )

    def _validar_empresa(self, empresa_id: int) -> None:
        if self.empresa_repository.get_by_id(empresa_id) is None:
            raise NotFoundError("Empresa no encontrada.")

    def _requerir_gestor_empresa(self, empresa_id: int, usuario_id: int) -> None:
        if not self.empresa_usuario_repository.has_any_role(
            empresa_id,
            usuario_id,
            (RolEmpresa.OWNER, RolEmpresa.RECRUITER),
        ):
            raise ForbiddenError("No tiene permisos para gestionar ofertas.")
