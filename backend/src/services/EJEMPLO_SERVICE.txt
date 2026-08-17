from sqlalchemy.orm import Session

from src.dtos.conductores_dto import CreateConductoresDTO, ConductoresResponseDTO
from src.mappers.conductores_mapper import to_conductores_response
from src.repositories.conductores_repository import ConductoresRepository


class ConductoresService:
    def __init__(self, db: Session):
        self.repo = ConductoresRepository(db)

    def create(self, dto: CreateConductoresDTO) -> ConductoresResponseDTO:
        conductor = self.repo.create(
            nombre=dto.nombre,
            licencia=dto.licencia,
            calificacion_promedio=dto.calificacion_promedio
        )
        return to_conductores_response(conductor)
    
    def get_by_id(self, conductor_id: int) -> ConductoresResponseDTO | None:
        conductor = self.repo.get_by_id(conductor_id)
        if conductor is None:
            return None
        return to_conductores_response(conductor)
    
    def update(self, conductor_id: int, dto: CreateConductoresDTO) -> ConductoresResponseDTO | None:
        conductor = self.repo.get_by_id(conductor_id)
        if conductor is None:
            return None
        
        conductor.nombre = dto.nombre or conductor.nombre
        conductor.licencia = dto.licencia or conductor.licencia
        conductor.calificacion_promedio = dto.calificacion_promedio or conductor.calificacion_promedio

        updated = self.repo.update(conductor)
        return to_conductores_response(updated)
    
    def delete(self, conductor_id: int) -> bool:
        conductor = self.repo.get_by_id(conductor_id)
        if conductor is None:
            return False
        
        self.repo.delete(conductor)
        return True
