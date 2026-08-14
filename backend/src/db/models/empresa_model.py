from pydantic import BaseModel, Field


class CreateEmpresaSchema(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: str | None = Field(default=None, max_length=255)


class UpdateEmpresaSchema(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: str | None = Field(default=None, max_length=255)


class DeleteEmpresaSchema(BaseModel):
    id: int


class GetEmpresaSchema(BaseModel):
    id: int
    nombre: str
    industria: str | None
    sitio_web: str | None