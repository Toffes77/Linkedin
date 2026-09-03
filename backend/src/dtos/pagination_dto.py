from typing import Generic, TypeVar

from pydantic import BaseModel


ItemDTO = TypeVar("ItemDTO")


class CursorPageDTO(BaseModel, Generic[ItemDTO]):
    items: list[ItemDTO]
    next_cursor: str | None
    has_more: bool
