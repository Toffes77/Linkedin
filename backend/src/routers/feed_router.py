from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.publicacion_dto import PublicacionResponseDTO
from src.schemas.publicación_schemas import GetPublicacionSchema
from src.services.feed_service import FeedService

router = APIRouter(tags=["feed"])


@router.get(
    "/usuarios/{usuario_id}/feed",
    response_model=list[GetPublicacionSchema],
)
def get_feed(
    usuario_id: int,
    page: int = 1,
    db: Session = Depends(get_db),
):
    publicaciones: list[PublicacionResponseDTO] = FeedService(db).get_feed(
        usuario_id,
        page=page,
    )
    return [GetPublicacionSchema.model_validate(publicacion) for publicacion in publicaciones]
