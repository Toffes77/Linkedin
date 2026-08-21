from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import UnauthorizedError
from src.utils.jwt import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token: str | None = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif request.headers.get("authorization"):
        raise UnauthorizedError("Missing or malformed Authorization header")
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise UnauthorizedError("Missing authentication token")

    payload = decode_token(token)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise UnauthorizedError("Invalid token payload")

    user = UsuarioRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")

    return user
