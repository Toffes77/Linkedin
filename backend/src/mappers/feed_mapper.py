from src.dtos.feed_dto import FeedPageDTO
from src.mappers.publicacion_mapper import PublicacionMapper
from src.schemas.feed_schema import FeedPageSchema


class FeedMapper:
    @staticmethod
    def to_response_schema(dto: FeedPageDTO) -> FeedPageSchema:
        return FeedPageSchema(
            items=[
                PublicacionMapper.to_card_schema(publicacion)
                for publicacion in dto.items
            ],
            next_cursor=dto.next_cursor,
            has_more=dto.has_more,
        )
