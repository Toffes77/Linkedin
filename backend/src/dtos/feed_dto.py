from pydantic import BaseModel

from src.dtos.publicacion_dto import PublicacionResponseDTO


class FeedPageDTO(BaseModel):
    items: list[PublicacionResponseDTO]
    next_cursor: str | None
    has_more: bool
