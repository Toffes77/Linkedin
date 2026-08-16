from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CreateEmpresaSchema(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: HttpUrl | None = None


class UpdateEmpresaSchema(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: HttpUrl | None = None


class GetEmpresaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    industria: str | None = None
    sitio_web: str | None = None