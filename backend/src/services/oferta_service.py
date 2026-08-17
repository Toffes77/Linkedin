from datetime import datetime

from sqlalchemy.orm import Session

from src.dtos.oferta_dto import (
    CreateOfertaDTO,
    OfertaResponseDTO,
    UpdateOfertaDTO,
)
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.oferta_repository import OfertaRepository
from src.utils.errors import NotFoundError


class OfertaService:
    def __init__(self, db: Session):
        self.repository = OfertaRepository(db)
        self.empresa_repository = EmpresaRepository(db)

    def create(self, oferta_data: CreateOfertaDTO) -> OfertaResponseDTO:
        self._validar_empresa(oferta_data.empresa_id)

        oferta = self.repository.create(oferta_data)
        if oferta.publicada:
            oferta.fecha_publicacion = datetime.now()
            oferta = self.repository.update(oferta, UpdateOfertaDTO())

        return OfertaResponseDTO.model_validate(oferta)

    def get_by_id(self, oferta_id: int) -> OfertaResponseDTO:
        oferta = self.repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        return OfertaResponseDTO.model_validate(oferta)

    def get_by_empresa(self, empresa_id: int) -> list[OfertaResponseDTO]:
        self._validar_empresa(empresa_id)
        ofertas = self.repository.get_by_empresa(empresa_id)
        return [OfertaResponseDTO.model_validate(oferta) for oferta in ofertas]

    def get_publicadas(self) -> list[OfertaResponseDTO]:
        ofertas = self.repository.get_publicadas()
        return [OfertaResponseDTO.model_validate(oferta) for oferta in ofertas]

    def update(
        self,
        oferta_id: int,
        oferta_data: UpdateOfertaDTO,
    ) -> OfertaResponseDTO:
        oferta = self.repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        if (
            not oferta.publicada
            and "publicada" in oferta_data.model_fields_set
            and oferta_data.publicada is True
        ):
            oferta.fecha_publicacion = datetime.now()

        oferta_actualizada = self.repository.update(oferta, oferta_data)
        return OfertaResponseDTO.model_validate(oferta_actualizada)

    def _validar_empresa(self, empresa_id: int) -> None:
        if self.empresa_repository.get_by_id(empresa_id) is None:
            raise NotFoundError("Empresa no encontrada.")
