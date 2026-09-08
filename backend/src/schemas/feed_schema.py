from pydantic import BaseModel

from src.schemas.publicación_schemas import GetPublicacionCardSchema


class FeedPageSchema(BaseModel):
    """Página del feed con cursor opaco para continuar la consulta."""

    items: list[GetPublicacionCardSchema]
    next_cursor: str | None
    has_more: bool
