from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.conductores_dto import CreateConductoresDTO, ConductoresResponseDTO
from src.schemas.conductores_schema import CreateConductoresSchema
from src.services.conductores_service import ConductoresService

router = APIRouter(prefix="/conductores", tags=["conductores"])


@router.post("/", response_model=ConductoresResponseDTO, status_code=status.HTTP_201_CREATED)
def create_conductor(payload: CreateConductoresSchema, db: Session = Depends(get_db)):
    """Crea un nuevo conductor."""
    dto = CreateConductoresDTO(**payload.model_dump())
    return ConductoresService(db).create(dto)

@router.get("/{conductor_id}", response_model=ConductoresResponseDTO)
def get_conductor(conductor_id: int, db: Session = Depends(get_db)):
    result = ConductoresService(db).get_by_id(conductor_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conductor no encontrado")
    return result

@router.put("/{conductor_id}", response_model=ConductoresResponseDTO)
def update_conductor(conductor_id: int, payload: CreateConductoresSchema, db: Session = Depends(get_db)):
    dto = CreateConductoresDTO(**payload.model_dump())
    result = ConductoresService(db).update(conductor_id, dto)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conductor no encontrado")
    return result

@router.delete("/{conductor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conductor(conductor_id: int, db: Session = Depends(get_db)):
    deleted = ConductoresService(db).delete(conductor_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conductor no encontrado")
