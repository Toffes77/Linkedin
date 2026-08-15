from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePublicacionSchema(BaseModel):
    texto: str = Field(min_length=1, max_length=3000)


class UpdatePublicacionSchema(BaseModel):
    texto: str | None = Field(
        default=None,
        min_length=1,
        max_length=3000
    )


class DeletePublicacionSchema(BaseModel):
    id: int


class GetPublicacionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    autor_id: int
    texto: str
    fecha: datetime