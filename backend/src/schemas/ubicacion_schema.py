from pydantic import BaseModel


class CiudadSchema(BaseModel):
    pais: str
    ciudad: str
    nombre: str
