from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


ItemSchema = TypeVar("ItemSchema")


class CursorPageSchema(BaseModel, Generic[ItemSchema]):
    model_config = ConfigDict(from_attributes=True)

    items: list[ItemSchema]
    next_cursor: str | None
    has_more: bool
