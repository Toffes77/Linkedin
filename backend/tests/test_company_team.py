import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.usuario_model import Usuario
from src.dtos.empresa_usuario_dto import MiembroEmpresaResponseDTO
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.services.empresa_usuario_service import EmpresaUsuarioService


class CompanyTeamRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.company = Empresa(nombre="Empresa principal")
        other_company = Empresa(nombre="Empresa ajena")
        self.db.add_all([self.company, other_company])
        self.db.flush()

        member_data = [
            ("Luca De Lauro", RolEmpresa.OWNER),
            ("Juan Cruz Maletti", RolEmpresa.OWNER),
            ("Santino Conca", RolEmpresa.RECRUITER),
            ("Benjamin Gomez", RolEmpresa.RECRUITER),
            ("Pedro Lopez", RolEmpresa.COLLABORATOR),
            ("Lucas Fernandez", RolEmpresa.COLLABORATOR),
        ]
        users = []
        for index, (name, role) in enumerate(member_data, start=1):
            user = Usuario(
                email=f"member{index}@example.com",
                nombre=name,
                password_hash=f"secret-hash-{index}",
                headline=f"Headline {index}",
                ciudad="Buenos Aires",
                foto_perfil_url=f"/imagenes/member-{index}.jpg" if index == 1 else None,
            )
            users.append(user)
            self.db.add(user)
            self.db.flush()
            self.db.add(
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=user.id,
                    rol=role,
                )
            )

        outsider = Usuario(
            email="outsider@example.com",
            nombre="Aaron Ajeno",
            password_hash="private-hash",
            headline="No pertenece",
            ciudad="Cordoba",
        )
        self.db.add(outsider)
        self.db.flush()
        self.db.add(
            EmpresaUsuario(
                empresa_id=other_company.id,
                usuario_id=outsider.id,
                rol=RolEmpresa.OWNER,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.query(EmpresaUsuario).delete()
        self.db.query(Usuario).delete()
        self.db.query(Empresa).delete()
        self.db.commit()
        self.db.close()

    def test_returns_every_role_ordered_by_priority_and_name(self):
        members = EmpresaUsuarioRepository(self.db).get_public_members(
            self.company.id
        )

        self.assertEqual(
            [(member.usuario.nombre, member.rol) for member in members],
            [
                ("Juan Cruz Maletti", RolEmpresa.OWNER),
                ("Luca De Lauro", RolEmpresa.OWNER),
                ("Benjamin Gomez", RolEmpresa.RECRUITER),
                ("Santino Conca", RolEmpresa.RECRUITER),
                ("Lucas Fernandez", RolEmpresa.COLLABORATOR),
                ("Pedro Lopez", RolEmpresa.COLLABORATOR),
            ],
        )

    def test_user_from_another_company_is_not_returned(self):
        members = EmpresaUsuarioRepository(self.db).get_public_members(
            self.company.id
        )

        self.assertNotIn("Aaron Ajeno", [member.usuario.nombre for member in members])

    def test_service_returns_only_public_member_fields(self):
        members = EmpresaUsuarioService(self.db).get_public_members(self.company.id)

        self.assertEqual(len(members), 6)
        self.assertEqual(
            set(members[0].model_dump()),
            {"usuario_id", "nombre", "headline", "foto_perfil_url", "rol"},
        )
        self.assertFalse(hasattr(members[0], "email"))
        self.assertFalse(hasattr(members[0], "password_hash"))


class CompanyTeamEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_db] = lambda: Mock()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_public_endpoint_exposes_the_safe_contract_without_authentication(self):
        members = [
            MiembroEmpresaResponseDTO(
                usuario_id=4,
                nombre="Juan Cruz Maletti",
                headline="Desarrollador",
                foto_perfil_url="/imagenes/member-4.jpg",
                rol=RolEmpresa.OWNER,
            ),
            MiembroEmpresaResponseDTO(
                usuario_id=8,
                nombre="Santino Conca",
                headline="Recursos Humanos",
                rol=RolEmpresa.RECRUITER,
            ),
            MiembroEmpresaResponseDTO(
                usuario_id=12,
                nombre="Pedro Lopez",
                headline="Backend Developer",
                rol=RolEmpresa.COLLABORATOR,
            ),
        ]

        with patch(
            "src.routers.empresa_router.EmpresaUsuarioService.get_public_members",
            return_value=members,
        ) as get_members:
            response = TestClient(app).get("/api/empresas/10/miembros")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            [item["rol"] for item in response.json()],
            ["OWNER", "RECRUITER", "COLLABORATOR"],
        )
        self.assertEqual(
            set(response.json()[0]),
            {"usuario_id", "nombre", "headline", "foto_perfil_url", "rol"},
        )
        self.assertNotIn("email", response.text)
        self.assertNotIn("password", response.text)
        get_members.assert_called_once_with(10)


if __name__ == "__main__":
    unittest.main()
