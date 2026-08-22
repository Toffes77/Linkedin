from src.db.models.conexiones_model import Conexion
from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    CreateConexionDTO,
    InvitacionRecibidaResponseDTO,
    ResumenRedResponseDTO,
    UpdateConexionDTO,
)
from src.schemas.conexiones_schema import (
    CreateConexionSchema,
    GetConexionSchema,
    UpdateConexionSchema,
    ResumenRedResponseSchema,
    InvitacionRecibidaResponseSchema,
)


class ConexionMapper:
    @staticmethod
    def to_create_dto(schema: CreateConexionSchema) -> CreateConexionDTO:
        return CreateConexionDTO(**schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdateConexionSchema) -> UpdateConexionDTO:
        return UpdateConexionDTO(**schema.model_dump())

    @staticmethod
    def to_model(data: CreateConexionDTO) -> Conexion:
        return Conexion(**data.model_dump())

    @staticmethod
    def apply_update(model: Conexion, data: UpdateConexionDTO) -> Conexion:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(model, field, value)
        return model

    @staticmethod
    def to_response_dto(model: Conexion) -> ConexionResponseDTO:
        return ConexionResponseDTO.model_validate(model)

    @staticmethod
    def to_response_schema(dto: ConexionResponseDTO) -> GetConexionSchema:
        return GetConexionSchema.model_validate(dto)

    @staticmethod
    def to_resumen_response_schema(
        dto: ResumenRedResponseDTO,
    ) -> ResumenRedResponseSchema:
        return ResumenRedResponseSchema(
            invitaciones_enviadas=dto.invitaciones_enviadas,
            contactos=dto.contactos,
            siguiendo=dto.siguiendo,
        )

    @staticmethod
    def to_invitacion_response_dto(conexion: Conexion) -> InvitacionRecibidaResponseDTO:
        from src.mappers.usuario_mapper import UsuarioMapper

        return InvitacionRecibidaResponseDTO(
            usuario_a=conexion.usuario_a,
            usuario_b=conexion.usuario_b,
            fecha=conexion.fecha,
            estado=conexion.estado,
            usuario=UsuarioMapper.to_response_dto(conexion.usuario_a_rel),
        )

    @staticmethod
    def to_invitacion_response_schema(
        dto: InvitacionRecibidaResponseDTO,
    ) -> InvitacionRecibidaResponseSchema:
        from src.mappers.usuario_mapper import UsuarioMapper

        return InvitacionRecibidaResponseSchema(
            usuario_a=dto.usuario_a,
            usuario_b=dto.usuario_b,
            fecha=dto.fecha,
            estado=dto.estado,
            usuario=UsuarioMapper.to_response_schema(dto.usuario),
        )
