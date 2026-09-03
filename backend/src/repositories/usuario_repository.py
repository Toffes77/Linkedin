from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, selectinload

from src.db.models.experiencia_model import Experiencia
from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import UpdateUsuarioDTO
from src.utils.email import normalize_email


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, usuario: Usuario) -> Usuario:
        usuario.email = normalize_email(usuario.email)
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        return self.db.query(Usuario).filter(Usuario.id == usuario_id).first()

    def get_by_email(self, email: str) -> Usuario | None:
        return (
            self.db.query(Usuario)
            .filter(func.lower(Usuario.email) == normalize_email(email))
            .first()
        )

    def search(
        self,
        texto: str,
        ciudad: str | None = None,
        *,
        limit: int = 21,
        after: tuple[str, int] | None = None,
    ) -> list[tuple[Usuario, str]]:
        patron = f"%{texto}%"
        sort_name = func.lower(Usuario.nombre)
        query = (
            self.db.query(Usuario, sort_name.label("sort_name"))
            .options(selectinload(Usuario.experiencias))
        )

        query = query.filter(
            or_(
                Usuario.nombre.ilike(patron),
                Usuario.headline.ilike(patron),
                Usuario.experiencias.any(Experiencia.puesto.ilike(patron)),
            )
        )

        if ciudad is not None:
            query = query.filter(Usuario.ciudad.ilike(f"%{ciudad}%"))

        if after is not None:
            name, usuario_id = after
            query = query.filter(
                or_(
                    sort_name > name,
                    and_(sort_name == name, Usuario.id > usuario_id),
                )
            )

        return query.order_by(sort_name.asc(), Usuario.id.asc()).limit(limit).all()

    def update(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def update_profile(
        self,
        usuario: Usuario,
        usuario_data: UpdateUsuarioDTO,
    ) -> Usuario:
        if usuario_data.nombre is not None:
            usuario.nombre = usuario_data.nombre
        if usuario_data.headline is not None:
            usuario.headline = usuario_data.headline
        if usuario_data.ciudad is not None:
            usuario.ciudad = usuario_data.ciudad

        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def update_profile_photo(
        self,
        usuario: Usuario,
        foto_perfil_url: str,
        *,
        commit: bool = True,
    ) -> Usuario:
        usuario.foto_perfil_url = foto_perfil_url
        if commit:
            self.db.commit()
            self.db.refresh(usuario)
        else:
            self.db.flush()
        return usuario

    def update_password_hash(self, usuario: Usuario, password_hash: str) -> Usuario:
        usuario.password_hash = password_hash
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
