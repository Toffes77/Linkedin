from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.auth_dto import LoginDTO, TokenDTO
from src.schemas.auth_schema import LoginSchema, MessageResponseSchema, TokenSchema
from src.services.auth_service import AuthService
from src.config.env import settings
from src.utils.jwt import ACCESS_TOKEN_EXPIRE_SECONDS
from src.utils.openapi import error_responses

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenSchema,
    summary="Iniciar sesión",
    description=(
        "Valida email y contraseña. Devuelve un JWT y lo establece también "
        "en la cookie HttpOnly access_token. No requiere autenticación previa."
    ),
    responses=error_responses(401),
)
def login(payload: LoginSchema, response: Response, db: Session = Depends(get_db)):
    dto = LoginDTO(**payload.model_dump())
    token: TokenDTO = AuthService(db).login(dto)
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return TokenSchema(**token.model_dump())


@router.post(
    "/logout",
    response_model=MessageResponseSchema,
    summary="Cerrar sesión",
    description=(
        "Elimina la cookie access_token. Es idempotente y no exige que exista "
        "una sesión válida."
    ),
)
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"message": "Sesión cerrada correctamente"}
