from sqlalchemy.orm import Session

from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa


class EmpresaUsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, empresa_usuario: EmpresaUsuario) -> EmpresaUsuario:
        self.db.add(empresa_usuario)
        self.db.commit()
        self.db.refresh(empresa_usuario)
        return empresa_usuario

    def get_by_empresa_and_usuario(
        self,
        empresa_id: int,
        usuario_id: int,
    ) -> EmpresaUsuario | None:
        return self.db.get(EmpresaUsuario, (empresa_id, usuario_id))

    def get_by_empresa(self, empresa_id: int) -> list[EmpresaUsuario]:
        return (
            self.db.query(EmpresaUsuario)
            .filter(EmpresaUsuario.empresa_id == empresa_id)
            .order_by(EmpresaUsuario.usuario_id)
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
    ) -> EmpresaUsuario:
        empresa_usuario.rol = rol
        self.db.commit()
        self.db.refresh(empresa_usuario)
        return empresa_usuario

    def delete(self, empresa_usuario: EmpresaUsuario) -> None:
        self.db.delete(empresa_usuario)
        self.db.commit()
