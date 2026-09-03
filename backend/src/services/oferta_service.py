from datetime import datetime

from sqlalchemy.orm import Session

from src.dtos.oferta_dto import (
    CreateOfertaDTO,
    OfertaEstadisticasDTO,
    OfertaResponseDTO,
    UpdateOfertaDTO,
)
from src.dtos.pagination_dto import CursorPageDTO
from src.mappers.oferta_mapper import OfertaMapper
from src.db.models.empresa_usuario_model import RolEmpresa
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.repositories.oferta_repository import OfertaRepository
from src.repositories.postulacion_repository import PostulacionRepository
from src.utils.datetime_utils import utc_now
from src.utils.errors import BadRequestError, ForbiddenError, NotFoundError
from src.utils.pagination_cursor import decode_cursor, encode_cursor


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

        datos_finales = oferta_data.model_copy(
            update={
                "fecha_publicacion": utc_now()
                if oferta_data.publicada
                else None
            }
        )
        oferta = self.repository.create(datos_finales)

        return OfertaMapper.to_response_dto(oferta)

    def get_by_id(
        self,
        oferta_id: int,
        usuario_actual_id: int | None = None,
    ) -> OfertaResponseDTO:
        oferta = self.repository.get_by_id(oferta_id)
        if oferta is None:
            raise NotFoundError("Oferta no encontrada.")

        if not oferta.publicada and not self._es_gestor_empresa(
            oferta.empresa_id,
            usuario_actual_id,
        ):
            raise NotFoundError("Oferta no encontrada.")

        return OfertaMapper.to_response_dto(oferta)

    def get_by_empresa(
        self,
        empresa_id: int,
        usuario_actual_id: int | None = None,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPageDTO[OfertaResponseDTO]:
        self._validar_empresa(empresa_id)
        include_drafts = self._es_gestor_empresa(empresa_id, usuario_actual_id)
        scope = {
            "empresa_id": empresa_id,
            "include_drafts": include_drafts,
        }
        after_id = self._decode_id_cursor(
            cursor,
            kind="company_offers",
            scope=scope,
        )
        rows = self.repository.get_by_empresa_page(
            empresa_id,
            published_only=not include_drafts,
            limit=limit + 1,
            after_id=after_id,
        )
        return self._build_page(
            rows,
            limit,
            kind="company_offers",
            scope=scope,
            cursor_values=lambda oferta: [oferta.id],
        )

    def get_publicadas(
        self,
        q: str | None = None,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPageDTO[OfertaResponseDTO]:
        titulo = q.strip() if q else None
        scope = {"q": titulo or None}
        after = self._decode_datetime_cursor(
            cursor,
            kind="published_offers",
            scope=scope,
        )
        rows = self.repository.get_publicadas(
            titulo or None,
            limit=limit + 1,
            after=after,
        )
        return self._build_page(
            rows,
            limit,
            kind="published_offers",
            scope=scope,
            cursor_values=lambda oferta: [
                oferta.fecha_publicacion.isoformat(),
                oferta.id,
            ],
        )

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
            oferta.fecha_publicacion = utc_now()

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
            dias_desde_publicacion = (utc_now() - oferta.fecha_publicacion).days

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
        if not self._es_gestor_empresa(empresa_id, usuario_id):
            raise ForbiddenError("No tiene permisos para gestionar ofertas.")

    def _es_gestor_empresa(
        self,
        empresa_id: int,
        usuario_id: int | None,
    ) -> bool:
        return usuario_id is not None and self.empresa_usuario_repository.has_any_role(
            empresa_id,
            usuario_id,
            (RolEmpresa.OWNER, RolEmpresa.RECRUITER),
        )

    @staticmethod
    def _decode_id_cursor(
        cursor: str | None,
        *,
        kind: str,
        scope: dict,
    ) -> int | None:
        if cursor is None:
            return None
        try:
            values = decode_cursor(
                cursor,
                expected_kind=kind,
                expected_scope=scope,
            )
            if len(values) != 1:
                raise ValueError
            return int(values[0])
        except (TypeError, ValueError) as exc:
            raise BadRequestError("Cursor de ofertas inválido.") from exc

    @staticmethod
    def _decode_datetime_cursor(
        cursor: str | None,
        *,
        kind: str,
        scope: dict,
    ) -> tuple[datetime, int] | None:
        if cursor is None:
            return None
        try:
            values = decode_cursor(
                cursor,
                expected_kind=kind,
                expected_scope=scope,
            )
            if len(values) != 2 or not isinstance(values[0], str):
                raise ValueError
            return datetime.fromisoformat(values[0]), int(values[1])
        except (TypeError, ValueError) as exc:
            raise BadRequestError("Cursor de ofertas inválido.") from exc

    @staticmethod
    def _build_page(
        rows,
        limit: int,
        *,
        kind: str,
        scope: dict,
        cursor_values,
    ) -> CursorPageDTO[OfertaResponseDTO]:
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            next_cursor = encode_cursor(
                kind,
                scope,
                cursor_values(page_rows[-1]),
            )
        return CursorPageDTO[OfertaResponseDTO](
            items=[OfertaMapper.to_response_dto(oferta) for oferta in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )
