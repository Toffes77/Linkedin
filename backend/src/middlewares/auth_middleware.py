from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import UnauthorizedError
from src.utils.jwt import decode_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing or malformed Authorization header")

    payload = decode_token(credentials.credentials)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise UnauthorizedError("Invalid token payload")

    user = UsuarioRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")

    return user
