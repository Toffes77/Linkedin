from src.db.models.conductores_model import Conductores
from src.dtos.conductores_dto import ConductoresResponseDTO


def to_conductores_response(conductor: Conductores) -> ConductoresResponseDTO:
    """Convierte un Model SQLAlchemy en un DTO de respuesta (sin campos sensibles)."""
    return ConductoresResponseDTO.model_validate(conductor)
