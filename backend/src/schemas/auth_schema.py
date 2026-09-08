from pydantic import BaseModel, EmailStr, Field


class LoginSchema(BaseModel):
    """Credenciales para obtener un JWT."""

    email: EmailStr = Field(description="Email registrado de la cuenta.")
    password: str = Field(description="Contraseña actual de la cuenta.")


class TokenSchema(BaseModel):
    """Token emitido por el login; también se guarda en una cookie HttpOnly."""

    access_token: str = Field(description="JWT de acceso.")
    token_type: str = Field(default="bearer", description="Esquema HTTP del token.")


class MessageResponseSchema(BaseModel):
    """Respuesta simple con un mensaje legible."""

    message: str = Field(description="Mensaje de resultado de la operación.")
