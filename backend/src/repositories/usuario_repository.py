from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from src.db.models.experiencia_model import Experiencia
from src.db.models.usuario_model import Usuario


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        return self.db.query(Usuario).filter(Usuario.id == usuario_id).first()

    def get_by_email(self, email: str) -> Usuario | None:
        return self.db.query(Usuario).filter(Usuario.email == email).first()

    def search(self, texto: str, ciudad: str | None = None) -> list[Usuario]:
        patron = f"%{texto}%"
        query = self.db.query(Usuario).options(selectinload(Usuario.experiencias))

        query = query.filter(
            or_(
                Usuario.nombre.ilike(patron),
                Usuario.headline.ilike(patron),
                Usuario.experiencias.any(Experiencia.puesto.ilike(patron)),
            )
        )

        if ciudad is not None:
            query = query.filter(Usuario.ciudad.ilike(f"%{ciudad}%"))

        return query.all()

    def update(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
