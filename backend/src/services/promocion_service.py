from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models.empresa_usuario_model import EMPRESA_USUARIO_UNIQUE_CONSTRAINT, RolEmpresa
from src.db.models.solicitud_contratacion_promocion_model import (
    SOLICITUD_PROMOCION_ACCEPTED_UNIQUE_INDEX,
    SOLICITUD_PROMOCION_PENDING_UNIQUE_INDEX,
    EstadoSolicitudContratacionPromocion,
)
from src.dtos.notificacion_dto import CreateNotificacionDTO
from src.dtos.pagination_dto import CursorPageDTO
from src.dtos.promocion_dto import (
    CreatePromocionDTO,
    CreateSolicitudContratacionPromocionDTO,
    EmpresaContratanteDTO,
    PromocionResponseDTO,
    SolicitudContratacionPromocionResponseDTO,
)
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper
from src.mappers.promocion_mapper import PromocionMapper
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.repositories.promocion_repository import PromocionRepository
from src.repositories.solicitud_contratacion_promocion_repository import SolicitudContratacionPromocionRepository
from src.services.notificacion_service import NotificacionService
from src.utils.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from src.utils.integrity import violates_constraint
from src.utils.pagination_cursor import decode_cursor, encode_cursor


class PromocionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PromocionRepository(db)
        self.hiring_request_repository = SolicitudContratacionPromocionRepository(db)
        self.company_repository = EmpresaRepository(db)
        self.membership_repository = EmpresaUsuarioRepository(db)
        self.notification_service = NotificacionService(db)

    def create(self, data: CreatePromocionDTO, current_user_id: int) -> PromocionResponseDTO:
        promotion = self.repository.create(PromocionMapper.to_model(data, current_user_id))
        return PromocionMapper.to_response_dto(promotion)

    def get_board_page(self, current_user_id: int, *, q: str | None, cursor: str | None = None, limit: int = 10) -> CursorPageDTO[PromocionResponseDTO]:
        title = q.strip() if q and q.strip() else None
        scope = {"usuario_id": current_user_id, "q": title or ""}
        after = self._decode_promotion_cursor(cursor, "board_promotions", scope)
        rows = self.repository.get_board_page(current_user_id, title=title, limit=limit + 1, after=after)
        return self._to_cursor_page(rows, limit, "board_promotions", scope, False)

    def get_mine(self, current_user_id: int, *, cursor: str | None = None, limit: int = 10) -> CursorPageDTO[PromocionResponseDTO]:
        scope = {"usuario_id": current_user_id}
        after = self._decode_promotion_cursor(cursor, "my_promotions", scope)
        rows = self.repository.get_by_user_page(current_user_id, limit=limit + 1, after=after)
        return self._to_cursor_page(rows, limit, "my_promotions", scope, True)

    def get_hiring_companies(self, promotion_id: int, current_user_id: int) -> list[EmpresaContratanteDTO]:
        promotion = self._get_basic_promotion(promotion_id)
        self._ensure_available(promotion.id)
        self._prevent_self_hiring(promotion.usuario_id, current_user_id)
        memberships = self.membership_repository.get_hiring_companies(current_user_id, promotion.usuario_id, promotion.id)
        return [PromocionMapper.company_to_dto(item) for item in memberships]

    def create_hiring_request(self, promotion_id: int, data: CreateSolicitudContratacionPromocionDTO, current_user_id: int) -> SolicitudContratacionPromocionResponseDTO:
        try:
            # Compartido con la aceptación: no se inserta una propuesta mientras
            # otra transacción está cerrando la misma promoción.
            promotion = self._get_basic_promotion(promotion_id, for_update=True)
            self._ensure_available(promotion.id)
            self._prevent_self_hiring(promotion.usuario_id, current_user_id)

            # Las mutaciones de rol bloquean esta misma empresa; la autorización
            # se vuelve a comprobar dentro de la transacción.
            company = self.company_repository.get_by_id_for_update(data.empresa_id)
            if company is None:
                raise NotFoundError("Empresa no encontrada.")
            if not self.membership_repository.has_any_role(data.empresa_id, current_user_id, (RolEmpresa.OWNER, RolEmpresa.RECRUITER)):
                raise ForbiddenError("No puede contratar en nombre de esta empresa.")

            # Coordina con altas de membresía de la persona candidata.
            self.membership_repository.lock_membership_scope(data.empresa_id, promotion.usuario_id)
            if self.membership_repository.get_by_empresa_and_usuario(data.empresa_id, promotion.usuario_id) is not None:
                raise ConflictError("El usuario ya pertenece a la empresa.")
            if self.hiring_request_repository.get_pending(promotion_id, data.empresa_id) is not None:
                raise ConflictError("La empresa ya tiene una propuesta pendiente para esta promoción.")

            request = self.hiring_request_repository.create(
                PromocionMapper.hiring_request_to_model(promotion_id, current_user_id, data), commit=False
            )
            request.empresa = company
            self.notification_service.create_many(
                [CreateNotificacionDTO(
                    usuario_id=promotion.usuario_id,
                    usuario_origen_id=current_user_id,
                    tipo="CONTRATACION_PROMOCION",
                    mensaje=f'{company.nombre} quiere contratarte a partir de tu promoción "{promotion.titulo}".',
                    promocion_id=promotion.id,
                    solicitud_contratacion_promocion_id=request.id,
                )],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(request)
        except IntegrityError as error:
            self.db.rollback()
            if violates_constraint(error, SOLICITUD_PROMOCION_PENDING_UNIQUE_INDEX):
                raise ConflictError("La empresa ya tiene una propuesta pendiente para esta promoción.") from error
            raise
        except Exception:
            self.db.rollback()
            raise
        return PromocionMapper.hiring_request_to_response_dto(request)

    def accept_hiring_request(self, request_id: int, current_user_id: int) -> SolicitudContratacionPromocionResponseDTO:
        try:
            accepted = self._accept_hiring_request_in_transaction(request_id, current_user_id)
            self.db.commit()
            self.db.refresh(accepted)
        except IntegrityError as error:
            self.db.rollback()
            if violates_constraint(error, EMPRESA_USUARIO_UNIQUE_CONSTRAINT):
                return self._complete_acceptance_after_membership_race(request_id, current_user_id)
            if violates_constraint(error, SOLICITUD_PROMOCION_ACCEPTED_UNIQUE_INDEX):
                raise ConflictError("La promoción ya fue contratada.") from error
            raise
        except Exception:
            self.db.rollback()
            raise
        return PromocionMapper.hiring_request_to_response_dto(accepted)

    def reject_hiring_request(self, request_id: int, current_user_id: int) -> SolicitudContratacionPromocionResponseDTO:
        try:
            request_preview = self.hiring_request_repository.get_by_id(request_id)
            if request_preview is None:
                raise NotFoundError("Propuesta de contratación no encontrada.")
            promotion = self._get_basic_promotion(request_preview.promocion_id, for_update=True)
            request = self.hiring_request_repository.get_by_id_for_update(request_id)
            if request is None:
                raise NotFoundError("Propuesta de contratación no encontrada.")
            if promotion.usuario_id != current_user_id:
                raise ForbiddenError("No puede rechazar una propuesta dirigida a otro usuario.")
            if request.estado != EstadoSolicitudContratacionPromocion.PENDIENTE:
                raise ConflictError("La propuesta ya fue respondida.")
            rejected = self.hiring_request_repository.reject(request, commit=False)
            self.db.commit()
            self.db.refresh(rejected)
        except Exception:
            self.db.rollback()
            raise
        return PromocionMapper.hiring_request_to_response_dto(rejected)

    def _accept_hiring_request_in_transaction(self, request_id: int, current_user_id: int):
        # El orden es siempre promoción -> solicitud. Así, el cierre masivo de
        # pendientes no puede formar un ciclo con otra aceptación o rechazo.
        request_preview = self.hiring_request_repository.get_by_id(request_id)
        if request_preview is None:
            raise NotFoundError("Propuesta de contratación no encontrada.")
        promotion = self._get_basic_promotion(request_preview.promocion_id, for_update=True)
        request = self.hiring_request_repository.get_by_id_for_update(request_id)
        if request is None:
            raise NotFoundError("Propuesta de contratación no encontrada.")
        if promotion.usuario_id != current_user_id:
            raise ForbiddenError("No puede aceptar una propuesta dirigida a otro usuario.")
        if request.estado != EstadoSolicitudContratacionPromocion.PENDIENTE:
            raise ConflictError("La propuesta ya fue respondida.")
        self._ensure_available(promotion.id)

        company = self.company_repository.get_by_id_for_update(request.empresa_id)
        if company is None:
            raise NotFoundError("Empresa no encontrada.")
        self.membership_repository.lock_membership_scope(request.empresa_id, current_user_id)
        membership = self.membership_repository.get_by_empresa_and_usuario(request.empresa_id, current_user_id)
        if membership is None:
            self.membership_repository.create(
                EmpresaUsuarioMapper.to_model_from_values(empresa_id=request.empresa_id, usuario_id=current_user_id, rol=RolEmpresa.COLLABORATOR),
                commit=False,
            )
        accepted = self.hiring_request_repository.accept(request, commit=False)
        accepted.empresa = company
        self.hiring_request_repository.reject_other_pending_for_promotion(promotion.id, accepted.id)
        return accepted

    def _complete_acceptance_after_membership_race(self, request_id: int, current_user_id: int) -> SolicitudContratacionPromocionResponseDTO:
        try:
            accepted = self._accept_hiring_request_in_transaction(request_id, current_user_id)
            self.db.commit()
            self.db.refresh(accepted)
        except IntegrityError as error:
            self.db.rollback()
            if violates_constraint(error, SOLICITUD_PROMOCION_ACCEPTED_UNIQUE_INDEX):
                raise ConflictError("La promoción ya fue contratada.") from error
            raise
        except Exception:
            self.db.rollback()
            raise
        return PromocionMapper.hiring_request_to_response_dto(accepted)

    def _get_promotion(self, promotion_id: int):
        promotion = self.repository.get_by_id(promotion_id)
        if promotion is None:
            raise NotFoundError("Promoción no encontrada.")
        return promotion

    def _get_basic_promotion(self, promotion_id: int, *, for_update: bool = False):
        promotion = self.repository.get_by_id_basic(promotion_id, for_update=for_update)
        if promotion is None:
            raise NotFoundError("Promoción no encontrada.")
        return promotion

    def _ensure_available(self, promotion_id: int) -> None:
        if self.hiring_request_repository.get_accepted_for_promotion(promotion_id) is not None:
            raise ConflictError("La promoción ya no está disponible.")

    @staticmethod
    def _prevent_self_hiring(candidate_user_id: int, current_user_id: int) -> None:
        if candidate_user_id == current_user_id:
            raise ConflictError("No puede contratar su propia promoción.")

    @staticmethod
    def _decode_promotion_cursor(cursor: str | None, kind: str, scope: dict) -> tuple[datetime, int] | None:
        if cursor is None:
            return None
        try:
            values = decode_cursor(cursor, expected_kind=kind, expected_scope=scope)
            if len(values) != 2 or not isinstance(values[0], str):
                raise ValueError
            return datetime.fromisoformat(values[0]), int(values[1])
        except (TypeError, ValueError) as exc:
            raise BadRequestError("Cursor de promociones inválido.") from exc

    @staticmethod
    def _to_cursor_page(rows, limit: int, kind: str, scope: dict, include_requests: bool) -> CursorPageDTO[PromocionResponseDTO]:
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(kind, scope, [last.fecha_creacion.isoformat(), last.id])
        return CursorPageDTO[PromocionResponseDTO](
            items=[PromocionMapper.to_response_dto(item, include_requests=include_requests) for item in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )
