from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.db.models.conexiones_model import Conexion
from src.dtos.conexiones_dto import CreateConexionDTO, UpdateConexionDTO


class ConexionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, conexion_data: CreateConexionDTO) -> Conexion:
        conexion = Conexion(**conexion_data.model_dump())
        self.db.add(conexion)
        self.db.commit()
        self.db.refresh(conexion)
        return conexion

    def get_by_id(self, usuario_a: int, usuario_b: int) -> Conexion | None:
        return self.db.get(Conexion, (usuario_a, usuario_b))

    def get_by_usuarios(self, usuario_a: int, usuario_b: int) -> Conexion | None:
        return (
            self.db.query(Conexion)
            .filter(
                or_(
                    (Conexion.usuario_a == usuario_a)
                    & (Conexion.usuario_b == usuario_b),
                    (Conexion.usuario_a == usuario_b)
                    & (Conexion.usuario_b == usuario_a),
                )
            )
            .first()
        )

    def get_by_usuario(self, usuario_id: int) -> list[Conexion]:
        return (
            self.db.query(Conexion)
            .filter(
                or_(
                    Conexion.usuario_a == usuario_id,
                    Conexion.usuario_b == usuario_id,
                )
            )
            .all()
        )

    def get_accepted_by_user(self, usuario_id: int) -> list[Conexion]:
        return (
            self.db.query(Conexion)
            .filter(
                Conexion.estado == "aceptada",
                or_(
                    Conexion.usuario_a == usuario_id,
                    Conexion.usuario_b == usuario_id,
                ),
            )
            .all()
        )

    def update(
        self,
        conexion: Conexion,
        conexion_data: UpdateConexionDTO,
    ) -> Conexion:
        for field, value in conexion_data.model_dump(exclude_unset=True).items():
            setattr(conexion, field, value)

        self.db.commit()
        self.db.refresh(conexion)
        return conexion
