from pydantic import BaseModel


class CiudadSchema(BaseModel):
    """Ciudad normalizada del catálogo disponible para perfiles."""

    pais: str
    ciudad: str
    nombre: str
