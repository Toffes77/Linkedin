from src.db.models.conexiones_model import Conexion
from src.dtos.conexiones_dto import (
    ConexionResponseDTO,
    CreateConexionDTO,
    UpdateConexionDTO,
)
from src.schemas.conexiones_schema import (
    CreateConexionSchema,
    GetConexionSchema,
    UpdateConexionSchema,
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
