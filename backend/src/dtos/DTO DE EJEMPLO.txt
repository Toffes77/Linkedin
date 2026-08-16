from pydantic import BaseModel


class CreateConductoresDTO(BaseModel):  # POST
    nombre: str
    licencia: str
    calificacion_promedio: float


class UpdateConductoresDTO(BaseModel):  # PUT/PATCH
    nombre: str | None = None
    licencia: str | None = None
    calificacion_promedio: float | None = None


class DeleteConductoresDTO(BaseModel):  # DELETE
    id: int


class GetConductoresDTO(BaseModel):  # GET (individual)
    id: int


class ConductoresResponseDTO(BaseModel):
    id: int
    nombre: str
    licencia: str
    calificacion_promedio: float

    model_config = {"from_attributes": True}
