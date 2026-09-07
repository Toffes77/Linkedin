import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, SessionLocal, engine, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.usuario_model import Usuario
from src.dtos.pagination_dto import CursorPageDTO
from src.dtos.empresa_usuario_dto import CreateEmpresaUsuarioDTO
from src.dtos.usuario_dto import UsuarioResponseDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.empresa_usuario_service import EmpresaUsuarioService
from src.utils.errors import BadRequestError, ForbiddenError


def make_user(index: int, name: str) -> Usuario:
    return Usuario(
        email=f"candidate-{index}@example.com",
        nombre=name,
        password_hash=f"hash-{index}",
        headline=f"Headline {index}",
        ciudad="Argentina, Córdoba",
        foto_perfil_url=f"/imagenes/candidate-{index}.jpg" if index == 4 else None,
    )


class CompanyMemberCandidateServiceTests(unittest.TestCase):
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
        self.other_company = Empresa(nombre="Empresa ajena")
        self.db.add_all([self.company, self.other_company])
        self.db.flush()

        self.owner = make_user(1, "Juan Owner")
        self.existing_recruiter = make_user(2, "Juan Recruiter")
        self.existing_collaborator = make_user(3, "Juan Collaborator")
        self.candidate_with_photo = make_user(4, "Juan Álvarez")
        self.candidate_without_photo = make_user(5, "juan Benítez")
        self.unrelated = make_user(6, "Persona Sin Coincidencia")
        self.db.add_all(
            [
                self.owner,
                self.existing_recruiter,
                self.existing_collaborator,
                self.candidate_with_photo,
                self.candidate_without_photo,
                self.unrelated,
            ]
        )
        self.db.flush()
        self.db.add_all(
            [
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.owner.id,
                    rol=RolEmpresa.OWNER,
                ),
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.existing_recruiter.id,
                    rol=RolEmpresa.RECRUITER,
                ),
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.existing_collaborator.id,
                    rol=RolEmpresa.COLLABORATOR,
                ),
                EmpresaUsuario(
                    empresa_id=self.other_company.id,
                    usuario_id=self.candidate_without_photo.id,
                    rol=RolEmpresa.COLLABORATOR,
                ),
                EmpresaUsuario(
                    empresa_id=self.other_company.id,
                    usuario_id=self.owner.id,
                    rol=RolEmpresa.OWNER,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.query(EmpresaUsuario).delete()
        self.db.query(Usuario).delete()
        self.db.query(Empresa).delete()
        self.db.commit()
        self.db.close()

    def test_search_by_name_excludes_every_existing_role(self):
        page = EmpresaUsuarioService(self.db).search_candidates(
            self.company.id,
            self.owner.id,
            "JUAN",
            limit=10,
        )

        self.assertEqual(
            [user.nombre for user in page.items],
            ["juan Benítez", "Juan Álvarez"],
        )
        self.assertIsNone(page.items[0].foto_perfil_url)
        self.assertEqual(page.items[1].foto_perfil_url, "/imagenes/candidate-4.jpg")
        self.assertTrue(all(user.headline for user in page.items))

    def test_member_of_another_company_remains_a_candidate(self):
        page = EmpresaUsuarioService(self.db).search_candidates(
            self.company.id,
            self.owner.id,
            "Benítez",
        )

        self.assertEqual([user.id for user in page.items], [self.candidate_without_photo.id])

    def test_search_uses_name_only_and_stable_cursor(self):
        self.candidate_with_photo.headline = "Especialista Encontrable"
        self.db.commit()

        no_name_match = EmpresaUsuarioService(self.db).search_candidates(
            self.company.id,
            self.owner.id,
            "Encontrable",
        )
        self.assertEqual(no_name_match.items, [])

        first = EmpresaUsuarioService(self.db).search_candidates(
            self.company.id,
            self.owner.id,
            "juan",
            limit=1,
        )
        second = EmpresaUsuarioService(self.db).search_candidates(
            self.company.id,
            self.owner.id,
            "juan",
            cursor=first.next_cursor,
            limit=1,
        )
        self.assertTrue(first.has_more)
        self.assertEqual(len({first.items[0].id, second.items[0].id}), 2)

        with self.assertRaises(BadRequestError):
            EmpresaUsuarioService(self.db).search_candidates(
                self.other_company.id,
                self.owner.id,
                "juan",
                cursor=first.next_cursor,
                limit=1,
            )

    def test_non_owner_cannot_search_company_candidates(self):
        with self.assertRaises(ForbiddenError):
            EmpresaUsuarioService(self.db).search_candidates(
                self.company.id,
                self.candidate_without_photo.id,
                "juan",
            )


class CompanyMemberCandidateEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=17)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_endpoint_returns_safe_paginated_user_results(self):
        candidate = UsuarioResponseDTO(
            id=8,
            nombre="Juan Cruz Maletti",
            headline="Técnico electrónico",
            ciudad="Argentina, Buenos Aires",
            foto_perfil_url="/imagenes/usuario-8.jpg",
            experiencias=[],
        )
        page = CursorPageDTO[UsuarioResponseDTO](
            items=[candidate],
            next_cursor=None,
            has_more=False,
        )

        with patch(
            "src.routers.empresa_router.EmpresaUsuarioService.search_candidates",
            return_value=page,
        ) as search:
            response = TestClient(app).get(
                "/api/empresas/3/usuarios/candidatos",
                params={"q": "juan", "limit": 10},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["items"][0]["id"], 8)
        self.assertEqual(response.json()["items"][0]["nombre"], candidate.nombre)
        self.assertNotIn("email", response.text)
        self.assertNotIn("password", response.text)
        search.assert_called_once_with(3, 17, "juan", cursor=None, limit=10)

    def test_short_queries_and_excessive_limits_are_rejected(self):
        client = TestClient(app)
        self.assertEqual(
            client.get(
                "/api/empresas/3/usuarios/candidatos",
                params={"q": "j"},
            ).status_code,
            422,
        )
        self.assertEqual(
            client.get(
                "/api/empresas/3/usuarios/candidatos",
                params={"q": "juan", "limit": 21},
            ).status_code,
            422,
        )


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La integración de candidatos requiere PostgreSQL.",
)
class CompanyMemberCandidatePostgresTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        with SessionLocal() as db:
            self.company = Empresa(nombre=f"Candidate company {suffix}")
            self.other_company = Empresa(nombre=f"Other company {suffix}")
            self.owner = Usuario(
                email=f"candidate-owner-{suffix}@example.com",
                nombre=f"Manager {suffix}",
                password_hash="hash",
                headline="Owner",
                ciudad="Argentina, Córdoba",
            )
            self.member = Usuario(
                email=f"candidate-member-{suffix}@example.com",
                nombre=f"Candidate Existing {suffix}",
                password_hash="hash",
                headline="Member",
                ciudad="Argentina, Córdoba",
            )
            self.candidate = Usuario(
                email=f"candidate-free-{suffix}@example.com",
                nombre=f"Candidate Available {suffix}",
                password_hash="hash",
                headline="Backend Developer",
                ciudad="Argentina, Córdoba",
            )
            db.add_all(
                [
                    self.company,
                    self.other_company,
                    self.owner,
                    self.member,
                    self.candidate,
                ]
            )
            db.flush()
            db.add_all(
                [
                    EmpresaUsuario(
                        empresa_id=self.company.id,
                        usuario_id=self.owner.id,
                        rol=RolEmpresa.OWNER,
                    ),
                    EmpresaUsuario(
                        empresa_id=self.company.id,
                        usuario_id=self.member.id,
                        rol=RolEmpresa.COLLABORATOR,
                    ),
                    EmpresaUsuario(
                        empresa_id=self.other_company.id,
                        usuario_id=self.candidate.id,
                        rol=RolEmpresa.RECRUITER,
                    ),
                ]
            )
            db.commit()
            self.company_id = self.company.id
            self.other_company_id = self.other_company.id
            self.owner_id = self.owner.id
            self.member_id = self.member.id
            self.candidate_id = self.candidate.id

    def tearDown(self):
        with SessionLocal() as db:
            db.query(EmpresaUsuario).filter(
                EmpresaUsuario.empresa_id.in_(
                    (self.company_id, self.other_company_id)
                )
            ).delete(synchronize_session=False)
            db.query(Usuario).filter(
                Usuario.id.in_((self.owner_id, self.member_id, self.candidate_id))
            ).delete(synchronize_session=False)
            db.query(Empresa).filter(
                Empresa.id.in_((self.company_id, self.other_company_id))
            ).delete(synchronize_session=False)
            db.commit()

    def test_candidate_can_be_selected_added_and_then_disappears(self):
        with SessionLocal() as db:
            service = EmpresaUsuarioService(db)
            before = service.search_candidates(
                self.company_id,
                self.owner_id,
                "Candidate",
            )
            self.assertEqual([item.id for item in before.items], [self.candidate_id])

            created = service.create(
                self.company_id,
                CreateEmpresaUsuarioDTO(
                    usuario_id=self.candidate_id,
                    rol=RolEmpresa.COLLABORATOR,
                ),
                self.owner_id,
            )
            self.assertEqual(created.usuario_id, self.candidate_id)

            after = service.search_candidates(
                self.company_id,
                self.owner_id,
                "Candidate",
            )
            self.assertEqual(after.items, [])


if __name__ == "__main__":
    unittest.main()
