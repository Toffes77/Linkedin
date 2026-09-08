from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.utils.text_validation import strip_non_blank


class CreateOfertaSchema(BaseModel):
    """Oferta creada por un OWNER o RECRUITER de la empresa."""

    empresa_id: int = Field(description="Empresa que publica la oferta.")
    titulo: str = Field(min_length=1, max_length=200, description="Título de la oferta; máximo 200 caracteres.")
    descripcion: str = Field(min_length=1, description="Descripción no vacía del puesto.")
    publicada: bool = Field(default=False, description="Si true, queda visible públicamente al crearla.")

    @field_validator("titulo", "descripcion", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class UpdateOfertaSchema(BaseModel):
    """Campos opcionales para actualizar una oferta propia de la empresa."""

    titulo: str | None = Field(default=None, min_length=1, max_length=200, description="Nuevo título.")
    descripcion: str | None = Field(default=None, min_length=1, description="Nueva descripción.")
    publicada: bool | None = Field(default=None, description="Publicar o despublicar la oferta.")

    @field_validator("titulo", "descripcion", mode="before")
    @classmethod
    def normalizar_texto(cls, value):
        return strip_non_blank(value)


class GetOfertaSchema(BaseModel):
    """Oferta visible según su estado y los permisos del lector."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    titulo: str
    descripcion: str
    publicada: bool
    fecha_publicacion: datetime | None = None


class GetOfertaEstadisticasSchema(BaseModel):
    """Estadísticas privadas de una oferta para OWNER o RECRUITER."""

    model_config = ConfigDict(from_attributes=True)

    oferta_id: int
    total_postulaciones: int
    postulaciones_por_estado: dict[str, int]
    dias_desde_publicacion: int | None = None
