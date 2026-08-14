from pydantic import BaseModel, Field


class CreateConductoresSchema(BaseModel):
    nombre: str = Field(min_length=2)
    licencia: str = Field(min_length=6)
    calificacion_promedio: float = Field(ge=0.0, le=5.0)


class UpdateConductoresSchema(BaseModel):
    nombre: str | None = Field(default=None, min_length=2)
    licencia: str | None = Field(default=None, min_length=6)
    calificacion_promedio: float | None = Field(default=None, ge=0.0, le=5.0)


class DeleteConductoresSchema(BaseModel):
    id: int


class GetConductoresSchema(BaseModel):
    id: int
