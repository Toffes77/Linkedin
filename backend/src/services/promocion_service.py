from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models.empresa_usuario_model import (
    EMPRESA_USUARIO_UNIQUE_CONSTRAINT,
    RolEmpresa,
)
from src.db.models.solicitud_contratacion_promocion_model import (
    SOLICITUD_PROMOCION_PENDING_UNIQUE_INDEX,
    EstadoSolicitudContratacionPromocion,
)
from src.dtos.notificacion_dto import CreateNotificacionDTO
from src.dtos.promocion_dto import (
    CreatePromocionDTO,
    CreateSolicitudContratacionPromocionDTO,
    EmpresaContratanteDTO,
    PromocionResponseDTO,
    PromocionesPaginadasDTO,
    SolicitudContratacionPromocionResponseDTO,
)
from src.mappers.empresa_usuario_mapper import EmpresaUsuarioMapper
from src.mappers.promocion_mapper import PromocionMapper
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.repositories.promocion_repository import PromocionRepository
from src.repositories.solicitud_contratacion_promocion_repository import (
    SolicitudContratacionPromocionRepository,
)
from src.services.notificacion_service import NotificacionService
from src.utils.errors import ConflictError, ForbiddenError, NotFoundError
from src.utils.integrity import violates_constraint


class PromocionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PromocionRepository(db)
        self.hiring_request_repository = SolicitudContratacionPromocionRepository(db)
        self.company_repository = EmpresaRepository(db)
        self.membership_repository = EmpresaUsuarioRepository(db)
        self.notification_service = NotificacionService(db)

    def create(
        self,
        data: CreatePromocionDTO,
        current_user_id: int,
    ) -> PromocionResponseDTO:
        promotion = self.repository.create(
            PromocionMapper.to_model(data, current_user_id)
        )
        return PromocionMapper.to_response_dto(promotion)

    def get_public_page(
        self,
        current_user_id: int,
        *,
        q: str | None,
        page: int,
        page_size: int,
    ) -> PromocionesPaginadasDTO:
        title = q.strip() if q and q.strip() else None
        promotions, total = self.repository.get_public_page(
            current_user_id,
            title=title,
            page=page,
            page_size=page_size,
        )
        return PromocionesPaginadasDTO(
            items=[PromocionMapper.to_response_dto(item) for item in promotions],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_mine(self, current_user_id: int) -> list[PromocionResponseDTO]:
        return [
            PromocionMapper.to_response_dto(item, include_requests=True)
            for item in self.repository.get_by_user(current_user_id)
        ]

    def get_hiring_companies(
        self,
        promotion_id: int,
        current_user_id: int,
    ) -> list[EmpresaContratanteDTO]:
        promotion = self._get_promotion(promotion_id)
        self._prevent_self_hiring(promotion.usuario_id, current_user_id)
        memberships = self.membership_repository.get_hiring_companies(
            current_user_id,
            promotion.usuario_id,
        )
        return [PromocionMapper.company_to_dto(item) for item in memberships]

    def create_hiring_request(
        self,
        promotion_id: int,
        data: CreateSolicitudContratacionPromocionDTO,
        current_user_id: int,
    ) -> SolicitudContratacionPromocionResponseDTO:
        promotion = self._get_promotion(promotion_id)
        self._prevent_self_hiring(promotion.usuario_id, current_user_id)
        company = self.company_repository.get_by_id(data.empresa_id)
        if company is None:
            raise NotFoundError("Empresa no encontrada.")
        if not self.membership_repository.has_any_role(
            data.empresa_id,
            current_user_id,
            (RolEmpresa.OWNER, RolEmpresa.RECRUITER),
        ):
            raise ForbiddenError("No puede contratar en nombre de esta empresa.")
        if self.membership_repository.get_by_empresa_and_usuario(
            data.empresa_id,
            promotion.usuario_id,
        ) is not None:
            raise ConflictError("El usuario ya pertenece a la empresa.")
        if self.hiring_request_repository.get_pending(
            promotion_id,
            data.empresa_id,
        ) is not None:
            raise ConflictError("La empresa ya tiene una propuesta pendiente para esta promoción.")

        try:
            request = self.hiring_request_repository.create(
                PromocionMapper.hiring_request_to_model(
                    promotion_id,
                    current_user_id,
                    data,
                ),
                commit=False,
            )
            self.notification_service.create_many(
                [
                    CreateNotificacionDTO(
                        usuario_id=promotion.usuario_id,
                        usuario_origen_id=current_user_id,
                        tipo="CONTRATACION_PROMOCION",
                        mensaje=(
                            f'{company.nombre} quiere contratarte a partir de tu '
                            f'promoción "{promotion.titulo}".'
                        ),
                        promocion_id=promotion.id,
                        solicitud_contratacion_promocion_id=request.id,
                    )
                ],
                commit=False,
            )
            self.db.commit()
            self.db.refresh(request)
        except IntegrityError as error:
            self.db.rollback()
            if violates_constraint(
                error,
                SOLICITUD_PROMOCION_PENDING_UNIQUE_INDEX,
            ):
                raise ConflictError(
                    "La empresa ya tiene una propuesta pendiente para esta promoción."
                ) from error
            raise
        except Exception:
            self.db.rollback()
            raise
        return PromocionMapper.hiring_request_to_response_dto(request)

    def accept_hiring_request(
        self,
        request_id: int,
        current_user_id: int,
    ) -> SolicitudContratacionPromocionResponseDTO:
        try:
            request = self.hiring_request_repository.get_by_id_for_update(request_id)
            if request is None:
                raise NotFoundError("Propuesta de contratación no encontrada.")
            if request.promocion.usuario_id != current_user_id:
                raise ForbiddenError("No puede aceptar una propuesta dirigida a otro usuario.")
            if request.estado != EstadoSolicitudContratacionPromocion.PENDIENTE:
                raise ConflictError("La propuesta ya fue respondida.")
            if self.company_repository.get_by_id(request.empresa_id) is None:
                raise NotFoundError("Empresa no encontrada.")

            membership = self.membership_repository.get_by_empresa_and_usuario(
                request.empresa_id,
                current_user_id,
            )
            if membership is None:
                self.membership_repository.create(
                    EmpresaUsuarioMapper.to_model_from_values(
                        empresa_id=request.empresa_id,
                        usuario_id=current_user_id,
                        rol=RolEmpresa.COLLABORATOR,
                    ),
                    commit=False,
                )
            accepted = self.hiring_request_repository.accept(request, commit=False)
            self.db.commit()
            self.db.refresh(accepted)
        except IntegrityError as error:
            self.db.rollback()
            if violates_constraint(error, EMPRESA_USUARIO_UNIQUE_CONSTRAINT):
                raise ConflictError("El usuario ya pertenece a la empresa.") from error
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

    @staticmethod
    def _prevent_self_hiring(candidate_user_id: int, current_user_id: int) -> None:
        if candidate_user_id == current_user_id:
            raise ConflictError("No puede contratar su propia promoción.")
