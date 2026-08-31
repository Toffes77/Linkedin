from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import UnauthorizedError
from src.utils.jwt import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


def _get_request_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    elif request.headers.get("authorization"):
        raise UnauthorizedError("Missing or malformed Authorization header")
    return request.cookies.get("access_token")


def _get_user_from_token(token: str, db: Session) -> Usuario:
    payload = decode_token(token)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise UnauthorizedError("Invalid token payload")

    user = UsuarioRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token = _get_request_token(request, credentials)

    if not token:
        raise UnauthorizedError("Missing authentication token")

    return _get_user_from_token(token, db)


def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario | None:
    token = _get_request_token(request, credentials)
    if not token:
        return None
    return _get_user_from_token(token, db)
