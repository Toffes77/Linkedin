from datetime import datetime

from sqlalchemy.orm import Session

from src.dtos.comentario_dto import (
    CantidadComentariosDTO,
    ComentarioResponseDTO,
    CrearComentarioDTO,
    GuardarComentarioDTO,
)
from src.dtos.pagination_dto import CursorPageDTO
from src.mappers.comentario_mapper import ComentarioMapper
from src.repositories.comentario_repository import ComentarioRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.utils.errors import BadRequestError, ForbiddenError, NotFoundError
from src.utils.pagination_cursor import decode_cursor, encode_cursor


class ComentarioService:
    def __init__(self, db: Session):
        self.repository = ComentarioRepository(db)
        self.publicacion_repository = PublicacionRepository(db)

    def create(
        self,
        publicacion_id: int,
        data: CrearComentarioDTO,
        usuario_id: int,
    ) -> ComentarioResponseDTO:
        self._require_publicacion(publicacion_id)
        contenido = self._normalizar_contenido(data.contenido)
        comentario = self.repository.create(
            GuardarComentarioDTO(
                publicacion_id=publicacion_id,
                usuario_id=usuario_id,
                contenido=contenido,
            )
        )
        return ComentarioMapper.to_response_dto(comentario)

    def reply(
        self,
        comentario_id: int,
        data: CrearComentarioDTO,
        usuario_id: int,
    ) -> ComentarioResponseDTO:
        comentario_padre = self.repository.get_by_id(comentario_id)
        if comentario_padre is None:
            raise NotFoundError("Comentario no encontrado.")

        self._require_publicacion(comentario_padre.publicacion_id)
        contenido = self._normalizar_contenido(data.contenido)
        respuesta = self.repository.create(
            GuardarComentarioDTO(
                publicacion_id=comentario_padre.publicacion_id,
                usuario_id=usuario_id,
                contenido=contenido,
                comentario_padre_id=comentario_padre.id,
            )
        )
        return ComentarioMapper.to_response_dto(respuesta)

    def list_roots(
        self,
        publicacion_id: int,
        *,
        cursor: str | None,
        limit: int,
    ) -> CursorPageDTO[ComentarioResponseDTO]:
        self._require_publicacion(publicacion_id)
        scope = {"publicacion_id": publicacion_id}
        after = self._decode_datetime_cursor(
            cursor,
            kind="comment_roots",
            scope=scope,
        )
        rows = self.repository.get_roots_page(
            publicacion_id,
            limit=limit + 1,
            after=after,
        )
        return self._build_page(rows, limit, kind="comment_roots", scope=scope)

    def list_replies(
        self,
        comentario_id: int,
        *,
        cursor: str | None,
        limit: int,
    ) -> CursorPageDTO[ComentarioResponseDTO]:
        comentario = self.repository.get_by_id(comentario_id)
        if comentario is None:
            raise NotFoundError("Comentario no encontrado.")
        self._require_publicacion(comentario.publicacion_id)
        scope = {"comentario_padre_id": comentario_id}
        after = self._decode_datetime_cursor(
            cursor,
            kind="comment_replies",
            scope=scope,
        )
        rows = self.repository.get_direct_replies_page(
            comentario_id,
            limit=limit + 1,
            after=after,
        )
        return self._build_page(rows, limit, kind="comment_replies", scope=scope)

    def count_by_publicacion(self, publicacion_id: int) -> CantidadComentariosDTO:
        self._require_publicacion(publicacion_id)
        return CantidadComentariosDTO(
            cantidad=self.repository.count_by_publicacion(publicacion_id)
        )

    def delete(self, comentario_id: int, usuario_id: int) -> None:
        comentario = self.repository.get_by_id(comentario_id)
        if comentario is None:
            raise NotFoundError("Comentario no encontrado.")
        if comentario.usuario_id != usuario_id:
            raise ForbiddenError("Solo el autor puede eliminar el comentario.")
        self.repository.delete(comentario)

    def _require_publicacion(self, publicacion_id: int) -> None:
        if self.publicacion_repository.get_by_id(publicacion_id) is None:
            raise NotFoundError("Publicación no encontrada.")

    @staticmethod
    def _normalizar_contenido(contenido: str) -> str:
        contenido_limpio = contenido.strip()
        if not contenido_limpio:
            raise BadRequestError("El comentario no puede estar vacío.")
        if len(contenido_limpio) > 1000:
            raise BadRequestError(
                "El comentario no puede superar los 1000 caracteres."
            )
        return contenido_limpio

    @staticmethod
    def _decode_datetime_cursor(
        cursor: str | None,
        *,
        kind: str,
        scope: dict,
    ) -> tuple[datetime, int] | None:
        if cursor is None:
            return None
        try:
            values = decode_cursor(
                cursor,
                expected_kind=kind,
                expected_scope=scope,
            )
            if len(values) != 2 or not isinstance(values[0], str):
                raise ValueError
            return datetime.fromisoformat(values[0]), int(values[1])
        except (TypeError, ValueError) as exc:
            raise BadRequestError("Cursor de comentarios inválido.") from exc

    @staticmethod
    def _build_page(
        rows,
        limit: int,
        *,
        kind: str,
        scope: dict,
    ) -> CursorPageDTO[ComentarioResponseDTO]:
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = [
            ComentarioMapper.to_response_dto(
                comentario,
                cantidad_respuestas=cantidad_respuestas,
            )
            for comentario, cantidad_respuestas in page_rows
        ]
        next_cursor = None
        if has_more and page_rows:
            last_comment = page_rows[-1][0]
            next_cursor = encode_cursor(
                kind,
                scope,
                [last_comment.fecha.isoformat(), last_comment.id],
            )
        return CursorPageDTO[ComentarioResponseDTO](
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )
