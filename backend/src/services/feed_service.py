from sqlalchemy.orm import Session

from src.dtos.publicacion_dto import PublicacionResponseDTO
from src.mappers.publicacion_mapper import PublicacionMapper
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.repositories.seguimiento_repository import SeguimientoRepository
from src.utils.errors import BadRequestError, NotFoundError


class FeedService:
    def __init__(self, db: Session):
        self.publicacion_repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.seguimiento_repository = SeguimientoRepository(db)

    def get_feed(
        self,
        usuario_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[PublicacionResponseDTO]:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

        if page < 1:
            raise BadRequestError("La página debe ser mayor o igual a 1.")

        if page_size < 1:
            raise BadRequestError("El tamaño de página debe ser mayor o igual a 1.")

        seguidos = self.seguimiento_repository.get_followed_ids(usuario_id)
        prioritarias = self.publicacion_repository.get_recent_by_authors(seguidos, 5)
        ids_prioritarios = {publicacion.id for publicacion in prioritarias}
        total_prioritarias = len(prioritarias)
        inicio = (page - 1) * page_size

        if inicio < total_prioritarias:
            prioritarias_pagina = prioritarias[inicio : inicio + page_size]
            cantidad_generales = page_size - len(prioritarias_pagina)
            offset_generales = 0
        else:
            prioritarias_pagina = []
            cantidad_generales = page_size
            offset_generales = inicio - total_prioritarias

        generales = self.publicacion_repository.get_general(
            ids_prioritarios,
            usuario_id,
            cantidad_generales,
            offset_generales,
        )
        publicaciones = prioritarias_pagina + generales
        return [
            PublicacionMapper.to_response_dto(publicacion)
            for publicacion in publicaciones
        ]
