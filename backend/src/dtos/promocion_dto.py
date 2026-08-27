from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.db.models.empresa_usuario_model import RolEmpresa
from src.db.models.solicitud_contratacion_promocion_model import EstadoSolicitudContratacionPromocion


class CreatePromocionDTO(BaseModel):
    titulo: str = Field(min_length=1, max_length=160)
    descripcion: str = Field(min_length=1, max_length=3000)

    @field_validator("titulo", "descripcion")
    @classmethod
    def trim_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("No puede contener solamente espacios.")
        return trimmed


class CreateSolicitudContratacionPromocionDTO(BaseModel):
    empresa_id: int = Field(gt=0)


class EmpresaContratanteDTO(BaseModel):
    empresa_id: int
    nombre: str
    foto_perfil_url: str | None = None
    rol: RolEmpresa


class SolicitudContratacionPromocionResponseDTO(BaseModel):
    id: int
    promocion_id: int
    empresa_id: int
    empresa_nombre: str
    empresa_foto_perfil_url: str | None = None
    solicitante_id: int
    estado: EstadoSolicitudContratacionPromocion
    fecha_creacion: datetime
    fecha_respuesta: datetime | None = None


class PromocionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    usuario_nombre: str
    usuario_headline: str
    usuario_foto_perfil_url: str | None = None
    titulo: str
    descripcion: str
    fecha_creacion: datetime
    estado: Literal["PENDIENTE", "PENDIENTE_CONTRATACION"] = "PENDIENTE"
    solicitudes_pendientes: list[SolicitudContratacionPromocionResponseDTO] = Field(default_factory=list)


class PromocionesPaginadasDTO(BaseModel):
    items: list[PromocionResponseDTO]
    page: int
    page_size: int
    total: int
