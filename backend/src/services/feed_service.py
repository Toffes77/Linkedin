from sqlalchemy.orm import Session

from src.dtos.publicacion_dto import PublicacionResponseDTO
from src.repositories.conexion_repository import ConexionRepository
from src.repositories.publicacion_repository import PublicacionRepository
from src.repositories.usuario_repository import UsuarioRepository
from src.utils.errors import NotFoundError


class FeedService:
    def __init__(self, db: Session):
        self.conexion_repository = ConexionRepository(db)
        self.publicacion_repository = PublicacionRepository(db)
        self.usuario_repository = UsuarioRepository(db)

    def get_feed(
        self,
        usuario_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> list[PublicacionResponseDTO]:
        if self.usuario_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuario no encontrado.")

        if page < 1:
            raise ValueError("La página debe ser mayor o igual a 1.")

        if page_size < 1:
            raise ValueError("El tamaño de página debe ser mayor o igual a 1.")

        conexiones = self.conexion_repository.get_accepted_by_user(usuario_id)
        usuarios_conectados = {
            conexion.usuario_b
            if conexion.usuario_a == usuario_id
            else conexion.usuario_a
            for conexion in conexiones
        }

        publicaciones = []
        for usuario_conectado_id in usuarios_conectados:
            publicaciones.extend(
                self.publicacion_repository.get_by_autor(usuario_conectado_id)
            )

        publicaciones = [
            publicacion
            for publicacion in publicaciones
            if publicacion.autor_id != usuario_id
        ]
        publicaciones.sort(key=lambda publicacion: publicacion.fecha, reverse=True)

        inicio = (page - 1) * page_size
        fin = inicio + page_size
        return [
            PublicacionResponseDTO.model_validate(publicacion)
            for publicacion in publicaciones[inicio:fin]
        ]
