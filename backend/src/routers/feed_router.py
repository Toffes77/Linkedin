from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.mappers.feed_mapper import FeedMapper
from src.schemas.feed_schema import FeedPageSchema
from src.services.feed_service import FeedService
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=FeedPageSchema)
def get_my_feed(
    cursor: str | None = Query(default=None, max_length=65_536),
    page_size: int = Query(default=20, ge=1, le=50),
    exclude_publicacion_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    page = FeedService(db).get_feed(
        current_user.id,
        cursor,
        page_size,
        exclude_publicacion_id,
    )
    return FeedMapper.to_response_schema(page)


@router.get(
    "/usuarios/{usuario_id}/feed",
    response_model=FeedPageSchema,
)
def get_feed(
    usuario_id: int,
    cursor: str | None = Query(default=None, max_length=65_536),
    page_size: int = Query(default=20, ge=1, le=50),
    exclude_publicacion_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    page = FeedService(db).get_feed(
        usuario_id,
        cursor,
        page_size,
        exclude_publicacion_id,
    )
    return FeedMapper.to_response_schema(page)
