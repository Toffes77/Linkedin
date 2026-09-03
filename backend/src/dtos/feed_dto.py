from pydantic import BaseModel

from src.dtos.publicacion_dto import PublicacionCardDTO


class FeedPageDTO(BaseModel):
    items: list[PublicacionCardDTO]
    next_cursor: str | None
    has_more: bool
