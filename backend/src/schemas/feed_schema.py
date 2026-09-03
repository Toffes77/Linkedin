from pydantic import BaseModel

from src.schemas.publicación_schemas import GetPublicacionCardSchema


class FeedPageSchema(BaseModel):
    items: list[GetPublicacionCardSchema]
    next_cursor: str | None
    has_more: bool
