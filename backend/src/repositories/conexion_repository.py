from sqlalchemy import func, or_, select, union, union_all
from sqlalchemy.orm import Session, selectinload, joinedload

from src.db.models.conexiones_model import Conexion
from src.db.models.usuario_model import Usuario
from src.dtos.conexiones_dto import CreateConexionDTO, UpdateConexionDTO
from src.mappers.conexion_mapper import ConexionMapper


class ConexionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        conexion_data: CreateConexionDTO,
        *,
        commit: bool = True,
    ) -> Conexion:
        usuario_a, usuario_b = self.ordenar_par(
            conexion_data.usuario_a,
            conexion_data.usuario_b,
        )
        solicitante_id = conexion_data.solicitante_id or conexion_data.usuario_a
        conexion = ConexionMapper.to_model(
            conexion_data.model_copy(
                update={
                    "usuario_a": usuario_a,
                    "usuario_b": usuario_b,
                    "solicitante_id": solicitante_id,
                }
            )
        )
        self.db.add(conexion)
        if commit:
            self.db.commit()
            self.db.refresh(conexion)
        else:
            self.db.flush()
        return conexion

    def get_by_id(self, usuario_a: int, usuario_b: int) -> Conexion | None:
        return self.db.get(Conexion, self.ordenar_par(usuario_a, usuario_b))

    def get_by_usuarios(self, usuario_a: int, usuario_b: int) -> Conexion | None:
        return self.get_by_id(usuario_a, usuario_b)

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

    def has_accepted_connection(self, usuario_a: int, usuario_b: int) -> bool:
        conexion = self.get_by_usuarios(usuario_a, usuario_b)
        return conexion is not None and conexion.estado == "aceptada"

    def count_pending_sent(self, usuario_id: int) -> int:
        return (
            self.db.query(Conexion)
            .filter(
                Conexion.solicitante_id == usuario_id,
                Conexion.estado == "pendiente",
            )
            .count()
        )

    def count_accepted_by_user(self, usuario_id: int) -> int:
        return (
            self.db.query(Conexion)
            .filter(
                Conexion.estado == "aceptada",
                or_(Conexion.usuario_a == usuario_id, Conexion.usuario_b == usuario_id),
            )
            .count()
        )

    def get_pending_received_by_user(self, usuario_id: int) -> list[Conexion]:
        return (
            self.db.query(Conexion)
            .options(
                joinedload(Conexion.solicitante_rel).selectinload(Usuario.experiencias)
            )
            .filter(
                or_(
                    Conexion.usuario_a == usuario_id,
                    Conexion.usuario_b == usuario_id,
                ),
                Conexion.solicitante_id != usuario_id,
                Conexion.estado == "pendiente",
            )
            .order_by(Conexion.fecha.desc())
            .all()
        )

    @staticmethod
    def ordenar_par(usuario_a: int, usuario_b: int) -> tuple[int, int]:
        return min(usuario_a, usuario_b), max(usuario_a, usuario_b)

    def get_second_degree_suggestions(self, usuario_id: int) -> list[Usuario]:
        conexiones_aceptadas = union_all(
            select(
                Conexion.usuario_a.label("usuario_id"),
                Conexion.usuario_b.label("conexion_id"),
            ).where(Conexion.estado == "aceptada"),
            select(
                Conexion.usuario_b.label("usuario_id"),
                Conexion.usuario_a.label("conexion_id"),
            ).where(Conexion.estado == "aceptada"),
        ).subquery("conexiones_aceptadas")

        conexiones_directas = conexiones_aceptadas.alias("conexiones_directas")
        conexiones_segundo_grado = conexiones_aceptadas.alias(
            "conexiones_segundo_grado"
        )

        relaciones_directas = union(
            select(Conexion.usuario_a.label("usuario_id")).where(
                Conexion.usuario_b == usuario_id,
                Conexion.estado.in_(("aceptada", "pendiente")),
            ),
            select(Conexion.usuario_b.label("usuario_id")).where(
                Conexion.usuario_a == usuario_id,
                Conexion.estado.in_(("aceptada", "pendiente")),
            ),
        ).subquery("relaciones_directas")

        candidatos = (
            select(
                conexiones_segundo_grado.c.conexion_id.label("usuario_id"),
                func.count(
                    func.distinct(conexiones_directas.c.conexion_id)
                ).label("conexiones_comunes"),
            )
            .select_from(conexiones_directas)
            .join(
                conexiones_segundo_grado,
                conexiones_segundo_grado.c.usuario_id
                == conexiones_directas.c.conexion_id,
            )
            .where(
                conexiones_directas.c.usuario_id == usuario_id,
                conexiones_segundo_grado.c.conexion_id != usuario_id,
                conexiones_segundo_grado.c.conexion_id.not_in(
                    select(relaciones_directas.c.usuario_id)
                ),
            )
            .group_by(conexiones_segundo_grado.c.conexion_id)
            .subquery("candidatos")
        )

        return (
            self.db.query(Usuario)
            .join(candidatos, Usuario.id == candidatos.c.usuario_id)
            .options(selectinload(Usuario.experiencias))
            .order_by(candidatos.c.conexiones_comunes.desc(), Usuario.id)
            .all()
        )

    def update(
        self,
        conexion: Conexion,
        conexion_data: UpdateConexionDTO,
        *,
        commit: bool = True,
    ) -> Conexion:
        ConexionMapper.apply_update(conexion, conexion_data)
        if commit:
            self.db.commit()
            self.db.refresh(conexion)
        else:
            self.db.flush()
        return conexion
