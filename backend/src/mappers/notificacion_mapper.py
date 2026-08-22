from src.db.models.notificacion_model import Notificacion
from src.dtos.notificacion_dto import CreateNotificacionDTO, NotificacionResponseDTO
from src.schemas.notificacion_schema import NotificacionResponseSchema


class NotificacionMapper:
    @staticmethod
    def to_model(dto: CreateNotificacionDTO) -> Notificacion:
        return Notificacion(**dto.model_dump())

    @staticmethod
    def to_response_dto(model: Notificacion) -> NotificacionResponseDTO:
        return NotificacionResponseDTO.model_validate(model)

    @staticmethod
    def to_response_schema(dto: NotificacionResponseDTO) -> NotificacionResponseSchema:
        return NotificacionResponseSchema(**dto.model_dump())
