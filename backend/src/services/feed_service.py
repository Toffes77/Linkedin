from datetime import date

from sqlalchemy.orm import Session

from src.dtos.publicacion_dto import PublicacionResponseDTO
from src.mappers.publicacion_mapper import PublicacionMapper
from src.repositories.conexion_repository import ConexionRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.seguimiento_repository import SeguimientoRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import BadRequestError, NotFoundError


class FeedService:
    def __init__(self, db: Session):
        self.publicacion_repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)
        self.conexion_repository = ConexionRepository(db)
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

        social_author_ids = self.seguimiento_repository.get_followed_ids(usuario_id)
        for conexion in self.conexion_repository.get_accepted_by_user(usuario_id):
            social_author_ids.add(
                conexion.usuario_b
                if conexion.usuario_a == usuario_id
                else conexion.usuario_a
            )

        publicaciones = self.publicacion_repository.get_feed(
            social_author_ids=social_author_ids,
            seed=date.today().toordinal() * 1009 + usuario_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return [
            PublicacionMapper.to_response_dto(publicacion)
            for publicacion in publicaciones
        ]
