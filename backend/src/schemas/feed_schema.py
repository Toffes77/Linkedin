from pydantic import BaseModel

from src.schemas.publicación_schemas import GetPublicacionSchema


class FeedPageSchema(BaseModel):
    items: list[GetPublicacionSchema]
    next_cursor: str | None
    has_more: bool
