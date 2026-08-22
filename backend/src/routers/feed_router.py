from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.dtos.publicacion_dto import PublicacionResponseDTO
from src.mappers.publicacion_mapper import PublicacionMapper
from src.schemas.publicación_schemas import GetPublicacionSchema
from src.services.feed_service import FeedService
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=list[GetPublicacionSchema])
def get_my_feed(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    publicaciones = FeedService(db).get_feed(current_user.id, page, page_size)
    return [PublicacionMapper.to_response_schema(publicacion) for publicacion in publicaciones]


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
    return [PublicacionMapper.to_response_schema(publicacion) for publicacion in publicaciones]
