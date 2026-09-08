from pydantic import BaseModel, Field


class ErrorResponseSchema(BaseModel):
    """Formato de las excepciones de dominio manejadas por la API."""

    error: str = Field(
        description="Nombre de la excepción de aplicación, por ejemplo NotFoundError."
    )
    message: str = Field(description="Mensaje legible que explica el error.")
