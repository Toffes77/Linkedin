from sqlalchemy import case, func
from sqlalchemy import and_
from sqlalchemy.orm import Session, aliased, contains_eager, joinedload

from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.usuario_model import Usuario


class EmpresaUsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        empresa_usuario: EmpresaUsuario,
        *,
        commit: bool = True,
    ) -> EmpresaUsuario:
        self.db.add(empresa_usuario)
        if commit:
            self.db.commit()
            self.db.refresh(empresa_usuario)
        else:
            self.db.flush()
        return empresa_usuario

    def get_by_empresa_and_usuario(
        self,
        empresa_id: int,
        usuario_id: int,
    ) -> EmpresaUsuario | None:
        return (
            self.db.query(EmpresaUsuario)
            .populate_existing()
            .filter(
                EmpresaUsuario.empresa_id == empresa_id,
                EmpresaUsuario.usuario_id == usuario_id,
            )
            .first()
        )

    def get_by_empresa(self, empresa_id: int) -> list[EmpresaUsuario]:
        return (
            self.db.query(EmpresaUsuario)
            .filter(EmpresaUsuario.empresa_id == empresa_id)
            .order_by(EmpresaUsuario.usuario_id)
            .all()
        )

    def get_public_members(self, empresa_id: int) -> list[EmpresaUsuario]:
        role_priority = case(
            (EmpresaUsuario.rol == RolEmpresa.OWNER, 0),
            (EmpresaUsuario.rol == RolEmpresa.RECRUITER, 1),
            (EmpresaUsuario.rol == RolEmpresa.COLLABORATOR, 2),
            else_=3,
        )
        return (
            self.db.query(EmpresaUsuario)
            .join(EmpresaUsuario.usuario)
            .options(contains_eager(EmpresaUsuario.usuario))
            .filter(EmpresaUsuario.empresa_id == empresa_id)
            .order_by(
                role_priority,
                func.lower(Usuario.nombre),
                Usuario.nombre,
                Usuario.id,
            )
            .all()
        )

    def get_by_usuario(self, usuario_id: int) -> list[EmpresaUsuario]:
        return (
            self.db.query(EmpresaUsuario)
            .options(joinedload(EmpresaUsuario.empresa))
            .filter(EmpresaUsuario.usuario_id == usuario_id)
            .order_by(EmpresaUsuario.rol, EmpresaUsuario.empresa_id)
            .all()
        )

    def get_hiring_companies(
        self,
        manager_user_id: int,
        candidate_user_id: int,
    ) -> list[EmpresaUsuario]:
        candidate_membership = aliased(EmpresaUsuario)
        return (
            self.db.query(EmpresaUsuario)
            .options(joinedload(EmpresaUsuario.empresa))
            .outerjoin(
                candidate_membership,
                and_(
                    candidate_membership.empresa_id == EmpresaUsuario.empresa_id,
                    candidate_membership.usuario_id == candidate_user_id,
                ),
            )
            .filter(
                EmpresaUsuario.usuario_id == manager_user_id,
                EmpresaUsuario.rol.in_((RolEmpresa.OWNER, RolEmpresa.RECRUITER)),
                candidate_membership.usuario_id.is_(None),
            )
            .order_by(EmpresaUsuario.empresa_id)
            .all()
        )

    def has_any_role(
        self,
        empresa_id: int,
        usuario_id: int,
        roles: tuple[RolEmpresa, ...],
    ) -> bool:
        return (
            self.db.query(EmpresaUsuario)
            .filter(
                EmpresaUsuario.empresa_id == empresa_id,
                EmpresaUsuario.usuario_id == usuario_id,
                EmpresaUsuario.rol.in_(roles),
            )
            .first()
            is not None
        )

    def get_user_ids_by_empresa_and_roles(
        self,
        empresa_id: int,
        roles: tuple[RolEmpresa, ...],
    ) -> list[int]:
        return [
            usuario_id
            for (usuario_id,) in self.db.query(EmpresaUsuario.usuario_id)
            .filter(
                EmpresaUsuario.empresa_id == empresa_id,
                EmpresaUsuario.rol.in_(roles),
            )
            .all()
        ]

    def count_owners(self, empresa_id: int) -> int:
        return (
            self.db.query(EmpresaUsuario)
            .filter(
                EmpresaUsuario.empresa_id == empresa_id,
                EmpresaUsuario.rol == RolEmpresa.OWNER,
            )
            .count()
        )

    def update(
        self,
        empresa_usuario: EmpresaUsuario,
        rol: RolEmpresa,
        *,
        commit: bool = True,
    ) -> EmpresaUsuario:
        empresa_usuario.rol = rol
        if commit:
            self.db.commit()
            self.db.refresh(empresa_usuario)
        else:
            self.db.flush()
        return empresa_usuario

    def delete(
        self,
        empresa_usuario: EmpresaUsuario,
        *,
        commit: bool = True,
    ) -> None:
        self.db.delete(empresa_usuario)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
