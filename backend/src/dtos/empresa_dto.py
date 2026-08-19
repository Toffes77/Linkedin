from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CreateEmpresaDTO(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: HttpUrl | None = Field(default=None, max_length=255)


class UpdateEmpresaDTO(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    industria: str | None = Field(default=None, max_length=100)
    sitio_web: HttpUrl | None = Field(default=None, max_length=255)


class EmpresaResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    industria: str | None = None
    sitio_web: str | None = None
    foto_perfil_url: str | None = None
