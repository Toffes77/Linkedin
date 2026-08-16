from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePublicacionDTO(BaseModel):
    autor_id: int
    texto: str = Field(min_length=1, max_length=3000)


class UpdatePublicacionDTO(BaseModel):
    texto: str | None = Field(default=None, min_length=1, max_length=3000)


class DeletePublicacionDTO(BaseModel):
    id: int


class PublicacionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_id: int
    texto: str
    fecha: datetime
