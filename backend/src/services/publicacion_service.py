from sqlalchemy.orm import Session

from src.dtos.publicacion_dto import (
    CreatePublicacionDTO,
    CreatePublicacionMultimediaDTO,
    MultimediaCreateDTO,
    PublicacionCardDTO,
    PublicacionResponseDTO,
    UpdatePublicacionDTO,
    UpdatePublicacionMultimediaDTO,
)
from src.mappers.publicacion_mapper import PublicacionMapper
from src.repositories.comentario_repository import ComentarioRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.reacciones_repository import ReaccionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import BadRequestError, ForbiddenError, NotFoundError
from src.utils.publication_media_storage import (
    MAX_PUBLICATION_MEDIA_ITEMS,
    UploadedPublicationFile,
    delete_publication_file,
    save_publication_file,
    validate_publication_files,
)


class PublicacionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.comentario_repository = ComentarioRepository(db)
        self.reaccion_repository = ReaccionRepository(db)

    def create(
        self,
        publicacion_data: CreatePublicacionDTO,
    ) -> PublicacionResponseDTO:
        self._validar_usuario(publicacion_data.autor_id)

        publicacion = self.repository.create(publicacion_data)
        return PublicacionMapper.to_response_dto(publicacion)

    def create_with_multimedia(
        self,
        publicacion_data: CreatePublicacionMultimediaDTO,
        files: list[UploadedPublicationFile],
    ) -> PublicacionResponseDTO:
        self._validar_usuario(publicacion_data.autor_id)
        validated_files = validate_publication_files(files)
        normalized_text = self._validate_content(
            publicacion_data.texto,
            len(validated_files),
        )
        publicacion_data = publicacion_data.model_copy(
            update={"texto": normalized_text}
        )

        saved_paths: list[str] = []
        try:
            publicacion = self.repository.create(publicacion_data, commit=False)
            items: list[MultimediaCreateDTO] = []
            for order, file in enumerate(validated_files):
                path = save_publication_file(publicacion.id, file)
                saved_paths.append(path)
                items.append(
                    MultimediaCreateDTO(
                        ruta=path,
                        tipo=file.media_type.value,
                        orden=order,
                    )
                )
            self.repository.add_multimedia(publicacion, items)
            self.db.commit()
        except Exception:
            self.db.rollback()
            for path in saved_paths:
                delete_publication_file(path, publicacion.id if "publicacion" in locals() else -1)
            raise

        created = self.repository.get_by_id(publicacion.id)
        if created is None:
            raise RuntimeError("No se pudo recuperar la publicación creada.")
        return PublicacionMapper.to_response_dto(created)

    def get_by_id(
        self,
        publicacion_id: int,
        usuario_actual_id: int | None = None,
    ) -> PublicacionCardDTO:
        publicacion = self.repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada.")

        return self.to_card_dtos([publicacion], usuario_actual_id)[0]

    def get_by_autor(
        self,
        autor_id: int,
        limit: int | None = None,
        offset: int = 0,
        usuario_actual_id: int | None = None,
    ) -> list[PublicacionCardDTO]:
        self._validar_usuario(autor_id)
        publicaciones = self.repository.get_by_autor(autor_id, limit, offset)
        return self.to_card_dtos(publicaciones, usuario_actual_id)

    def to_card_dtos(
        self,
        publicaciones,
        usuario_actual_id: int | None,
    ) -> list[PublicacionCardDTO]:
        publicacion_ids = [publicacion.id for publicacion in publicaciones]
        conteos = {
            publicacion_id: {
                "like": 0,
                "celebrar": 0,
                "apoyar": 0,
                "interesante": 0,
            }
            for publicacion_id in publicacion_ids
        }
        reacciones_actuales: dict[int, str] = {}
        for publicacion_id, tipo, cantidad, es_reaccion_actual in (
            self.reaccion_repository.summarize_by_publicaciones(
                publicacion_ids,
                usuario_actual_id,
            )
        ):
            conteos[publicacion_id][tipo] = cantidad
            if es_reaccion_actual:
                reacciones_actuales[publicacion_id] = tipo
        comentarios = self.comentario_repository.count_by_publicaciones(
            publicacion_ids
        )
        return [
            PublicacionMapper.to_card_dto(
                publicacion,
                reacciones=conteos[publicacion.id],
                mi_reaccion=reacciones_actuales.get(publicacion.id),
                cantidad_comentarios=comentarios.get(publicacion.id, 0),
            )
            for publicacion in publicaciones
        ]

    def update(
        self,
        publicacion_id: int,
        usuario_id: int,
        publicacion_data: UpdatePublicacionDTO,
    ) -> PublicacionResponseDTO:
        publicacion = self._obtener_y_validar_autor(publicacion_id, usuario_id)
        if "texto" in publicacion_data.model_fields_set:
            normalized_text = self._validate_content(
                publicacion_data.texto,
                len(publicacion.multimedia),
            )
            publicacion_data = publicacion_data.model_copy(
                update={"texto": normalized_text}
            )
        publicacion_actualizada = self.repository.update(
            publicacion,
            publicacion_data,
        )
        return PublicacionMapper.to_response_dto(publicacion_actualizada)

    def update_with_multimedia(
        self,
        publicacion_id: int,
        usuario_id: int,
        publicacion_data: UpdatePublicacionMultimediaDTO,
        kept_ids: list[int],
        files: list[UploadedPublicationFile],
    ) -> PublicacionResponseDTO:
        publicacion = self._obtener_y_validar_autor(publicacion_id, usuario_id)
        if len(kept_ids) != len(set(kept_ids)):
            raise BadRequestError("La selección de multimedia contiene elementos repetidos.")
        existing_by_id = {item.id: item for item in publicacion.multimedia}
        if any(item_id not in existing_by_id for item_id in kept_ids):
            raise ForbiddenError("No podés modificar multimedia de otra publicación.")
        if len(kept_ids) + len(files) > MAX_PUBLICATION_MEDIA_ITEMS:
            raise BadRequestError(
                f"Una publicación puede incluir hasta {MAX_PUBLICATION_MEDIA_ITEMS} archivos."
            )

        validated_files = validate_publication_files(files)
        normalized_text = self._validate_content(
            publicacion_data.texto,
            len(kept_ids) + len(validated_files),
        )
        publicacion_data = publicacion_data.model_copy(
            update={"texto": normalized_text}
        )
        removed = [item for item in publicacion.multimedia if item.id not in kept_ids]
        removed_paths = [item.ruta for item in removed]
        saved_paths: list[str] = []
        try:
            self.repository.update(
                publicacion,
                publicacion_data,
                commit=False,
            )
            new_items: list[MultimediaCreateDTO] = []
            for offset, file in enumerate(validated_files):
                path = save_publication_file(publicacion.id, file)
                saved_paths.append(path)
                new_items.append(
                    MultimediaCreateDTO(
                        ruta=path,
                        tipo=file.media_type.value,
                        orden=len(kept_ids) + offset,
                    )
                )
            self.repository.sync_multimedia(publicacion, kept_ids, new_items)
            self.db.commit()
        except Exception:
            self.db.rollback()
            for path in saved_paths:
                delete_publication_file(path, publicacion.id)
            raise

        for path in removed_paths:
            delete_publication_file(path, publicacion.id)
        updated = self.repository.get_by_id(publicacion.id)
        if updated is None:
            raise RuntimeError("No se pudo recuperar la publicación actualizada.")
        return PublicacionMapper.to_response_dto(updated)

    def delete(self, publicacion_id: int, usuario_id: int) -> None:
        publicacion = self._obtener_y_validar_autor(publicacion_id, usuario_id)
        paths = [item.ruta for item in publicacion.multimedia]
        try:
            self.repository.delete(publicacion, commit=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        for path in paths:
            delete_publication_file(path, publicacion_id)

    def _validar_usuario(self, usuario_id: int) -> None:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

    def _obtener_y_validar_autor(self, publicacion_id: int, usuario_id: int):
        publicacion = self.repository.get_by_id(publicacion_id)
        if publicacion is None:
            raise NotFoundError("Publicación no encontrada.")

        if publicacion.autor_id != usuario_id:
            raise ForbiddenError(
                "Solo el autor puede modificar o eliminar la publicación."
            )

        return publicacion

    @staticmethod
    def _validate_content(text: str | None, media_count: int) -> str:
        normalized_text = "" if text is None else text.strip()
        if text and not normalized_text:
            raise BadRequestError(
                "El texto no puede contener solamente espacios en blanco."
            )
        if not normalized_text and media_count == 0:
            raise BadRequestError("La publicación debe incluir texto o multimedia.")
        return normalized_text
