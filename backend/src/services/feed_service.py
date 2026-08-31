import secrets

from sqlalchemy.orm import Session

from src.dtos.feed_dto import FeedPageDTO
from src.mappers.publicacion_mapper import PublicacionMapper
from src.repositories.conexion_repository import ConexionRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.seguimiento_repository import SeguimientoRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import BadRequestError, NotFoundError
from src.utils.feed_cursor import FeedCursor, decode_feed_cursor, encode_feed_cursor


MAX_FEED_PAGE_SIZE = 50


class FeedService:
    def __init__(self, db: Session):
        self.publicacion_repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.conexion_repository = ConexionRepository(db)
        self.seguimiento_repository = SeguimientoRepository(db)

    def get_feed(
        self,
        usuario_id: int,
        cursor: str | None = None,
        page_size: int = 20,
        excluded_publicacion_id: int | None = None,
    ) -> FeedPageDTO:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

        if not 1 <= page_size <= MAX_FEED_PAGE_SIZE:
            raise BadRequestError(
                f"El tamaño de página debe estar entre 1 y {MAX_FEED_PAGE_SIZE}."
            )

        if cursor is None:
            social_author_ids = self._get_social_author_ids(usuario_id)
            seed = secrets.randbelow(2_147_483_648)
            visibility_snapshot = self.publicacion_repository.get_visibility_snapshot()
            snapshot_max_id = self.publicacion_repository.get_max_id(
                visibility_snapshot
            )
            after = None
            session_excluded_id = excluded_publicacion_id
        else:
            try:
                cursor_data = decode_feed_cursor(cursor)
            except ValueError as exc:
                raise BadRequestError("Cursor de feed inválido.") from exc
            if cursor_data.usuario_id != usuario_id:
                raise BadRequestError("Cursor de feed inválido para este usuario.")
            if (
                excluded_publicacion_id is not None
                and excluded_publicacion_id
                != cursor_data.excluded_publicacion_id
            ):
                raise BadRequestError("El cursor no corresponde al filtro solicitado.")
            social_author_ids = set(cursor_data.social_author_ids)
            seed = cursor_data.seed
            snapshot_max_id = cursor_data.snapshot_max_id
            visibility_snapshot = cursor_data.visibility_snapshot
            after = cursor_data.position
            session_excluded_id = cursor_data.excluded_publicacion_id

        rows = self.publicacion_repository.get_feed_page(
            social_author_ids=social_author_ids,
            seed=seed,
            snapshot_max_id=snapshot_max_id,
            visibility_snapshot=visibility_snapshot,
            limit=page_size + 1,
            after=after,
            excluded_publicacion_id=session_excluded_id,
        )
        has_more = len(rows) > page_size
        page_rows = rows[:page_size]
        next_cursor = None
        if has_more and page_rows:
            next_cursor = encode_feed_cursor(
                FeedCursor(
                    usuario_id=usuario_id,
                    seed=seed,
                    snapshot_max_id=snapshot_max_id,
                    visibility_snapshot=visibility_snapshot,
                    social_author_ids=tuple(sorted(social_author_ids)),
                    excluded_publicacion_id=session_excluded_id,
                    position=page_rows[-1].position,
                )
            )

        return FeedPageDTO(
            items=[
                PublicacionMapper.to_response_dto(row.publicacion)
                for row in page_rows
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _get_social_author_ids(self, usuario_id: int) -> set[int]:
        social_author_ids = self.seguimiento_repository.get_followed_ids(usuario_id)
        for conexion in self.conexion_repository.get_accepted_by_user(usuario_id):
            social_author_ids.add(
                conexion.usuario_b
                if conexion.usuario_a == usuario_id
                else conexion.usuario_a
            )
        return social_author_ids
