from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import (
    CreateUsuarioDTO,
    PasswordUpdateResponseDTO,
    UpdatePasswordDTO,
    UpdateUsuarioDTO,
    UsuarioResponseDTO,
)
from src.schemas.usuario_schema import (
    CreateUsuarioSchema,
    GetUsuarioSchema,
    PasswordUpdateResponseSchema,
    UpdatePasswordSchema,
    UpdateUsuarioSchema,
)


class UsuarioMapper:
    @staticmethod
    def to_create_dto(schema: CreateUsuarioSchema) -> CreateUsuarioDTO:
        return CreateUsuarioDTO(**schema.model_dump())

    @staticmethod
    def to_update_dto(schema: UpdateUsuarioSchema) -> UpdateUsuarioDTO:
        return UpdateUsuarioDTO(**schema.model_dump(exclude_unset=True))

    @staticmethod
    def to_update_password_dto(schema: UpdatePasswordSchema) -> UpdatePasswordDTO:
        return UpdatePasswordDTO(**schema.model_dump())

    @staticmethod
    def to_password_update_response_schema(
        dto: PasswordUpdateResponseDTO,
    ) -> PasswordUpdateResponseSchema:
        return PasswordUpdateResponseSchema(**dto.model_dump())

    @staticmethod
    def to_model(data: CreateUsuarioDTO, password_hash: str) -> Usuario:
        return Usuario(
            email=data.email,
            password_hash=password_hash,
            nombre=data.nombre,
            headline=data.headline,
            ciudad=data.ciudad,
        )

    @staticmethod
    def to_response_dto(usuario: Usuario) -> UsuarioResponseDTO:
        return UsuarioResponseDTO.model_validate(usuario)

    @staticmethod
    def to_response_schema(dto: UsuarioResponseDTO) -> GetUsuarioSchema:
        return GetUsuarioSchema.model_validate(dto)
