from fastapi import Depends, Header
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import UnauthorizedError
from src.utils.jwt import decode_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise UnauthorizedError("Invalid token payload")

    user = UsuarioRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")

    return user
