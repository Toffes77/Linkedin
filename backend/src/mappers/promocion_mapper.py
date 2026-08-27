from src.db.models.promocion_model import Promocion
from src.db.models.solicitud_contratacion_promocion_model import (
    EstadoSolicitudContratacionPromocion,
    SolicitudContratacionPromocion,
)
from src.dtos.promocion_dto import (
    CreatePromocionDTO,
    CreateSolicitudContratacionPromocionDTO,
    EmpresaContratanteDTO,
    PromocionResponseDTO,
    PromocionesPaginadasDTO,
    SolicitudContratacionPromocionResponseDTO,
)
from src.schemas.promocion_schema import (
    CreatePromocionSchema,
    CreateSolicitudContratacionPromocionSchema,
    GetEmpresaContratanteSchema,
    GetPromocionSchema,
    GetPromocionesPaginadasSchema,
    GetSolicitudContratacionPromocionSchema,
)


class PromocionMapper:
    @staticmethod
    def to_create_dto(schema: CreatePromocionSchema) -> CreatePromocionDTO:
        return CreatePromocionDTO(**schema.model_dump())

    @staticmethod
    def to_model(data: CreatePromocionDTO, usuario_id: int) -> Promocion:
        return Promocion(usuario_id=usuario_id, **data.model_dump())

    @staticmethod
    def to_hiring_request_dto(
        schema: CreateSolicitudContratacionPromocionSchema,
    ) -> CreateSolicitudContratacionPromocionDTO:
        return CreateSolicitudContratacionPromocionDTO(**schema.model_dump())

    @staticmethod
    def hiring_request_to_model(
        promocion_id: int,
        solicitante_id: int,
        data: CreateSolicitudContratacionPromocionDTO,
    ) -> SolicitudContratacionPromocion:
        return SolicitudContratacionPromocion(
            promocion_id=promocion_id,
            empresa_id=data.empresa_id,
            solicitante_id=solicitante_id,
            estado=EstadoSolicitudContratacionPromocion.PENDIENTE,
        )

    @staticmethod
    def hiring_request_to_response_dto(
        model: SolicitudContratacionPromocion,
    ) -> SolicitudContratacionPromocionResponseDTO:
        return SolicitudContratacionPromocionResponseDTO(
            id=model.id,
            promocion_id=model.promocion_id,
            empresa_id=model.empresa_id,
            empresa_nombre=model.empresa.nombre,
            empresa_foto_perfil_url=model.empresa.foto_perfil_url,
            solicitante_id=model.solicitante_id,
            estado=model.estado,
            fecha_creacion=model.fecha_creacion,
            fecha_respuesta=model.fecha_respuesta,
        )

    @classmethod
    def to_response_dto(
        cls,
        model: Promocion,
        *,
        include_requests: bool = False,
    ) -> PromocionResponseDTO:
        pending_requests = []
        if include_requests:
            pending_requests = [
                cls.hiring_request_to_response_dto(request)
                for request in model.solicitudes_contratacion
                if request.estado == EstadoSolicitudContratacionPromocion.PENDIENTE
            ]
        return PromocionResponseDTO(
            id=model.id,
            usuario_id=model.usuario_id,
            usuario_nombre=model.usuario.nombre,
            usuario_headline=model.usuario.headline,
            usuario_foto_perfil_url=model.usuario.foto_perfil_url,
            titulo=model.titulo,
            descripcion=model.descripcion,
            fecha_creacion=model.fecha_creacion,
            estado="PENDIENTE_CONTRATACION" if pending_requests else "PENDIENTE",
            solicitudes_pendientes=pending_requests,
        )

    @staticmethod
    def company_to_dto(membership) -> EmpresaContratanteDTO:
        return EmpresaContratanteDTO(
            empresa_id=membership.empresa_id,
            nombre=membership.empresa.nombre,
            foto_perfil_url=membership.empresa.foto_perfil_url,
            rol=membership.rol,
        )

    @staticmethod
    def to_response_schema(dto: PromocionResponseDTO) -> GetPromocionSchema:
        return GetPromocionSchema.model_validate(dto)

    @staticmethod
    def to_page_schema(dto: PromocionesPaginadasDTO) -> GetPromocionesPaginadasSchema:
        return GetPromocionesPaginadasSchema(**dto.model_dump())

    @staticmethod
    def company_to_schema(dto: EmpresaContratanteDTO) -> GetEmpresaContratanteSchema:
        return GetEmpresaContratanteSchema.model_validate(dto)

    @staticmethod
    def hiring_request_to_schema(
        dto: SolicitudContratacionPromocionResponseDTO,
    ) -> GetSolicitudContratacionPromocionSchema:
        return GetSolicitudContratacionPromocionSchema.model_validate(dto)
