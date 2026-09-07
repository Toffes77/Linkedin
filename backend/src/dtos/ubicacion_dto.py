from pydantic import BaseModel


class CiudadDTO(BaseModel):
    pais: str
    ciudad: str
    nombre: str
