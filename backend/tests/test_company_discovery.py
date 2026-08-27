import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import RolEmpresa
from src.dtos.empresa_dto import EmpresaResponseDTO
from src.dtos.empresa_usuario_dto import MiEmpresaResponseDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.empresa_service import EmpresaService
from src.services.empresa_usuario_service import EmpresaUsuarioService


def company(company_id: int, name: str):
    return SimpleNamespace(
        id=company_id,
        nombre=name,
        industria="Tecnología",
        sitio_web="https://example.com",
        foto_perfil_url=f"/imagenes/empresa_{company_id}.png",
    )


class CompanyDiscoveryTests(unittest.TestCase):
    def test_search_service_uses_repository_and_returns_public_data(self):
        service = EmpresaService(Mock())
        service.repository = Mock()
        service.repository.search_by_name.return_value = [company(1, "Tech Solutions")]

        result = service.search("tech")

        service.repository.search_by_name.assert_called_once_with("tech")
        self.assertEqual(result[0].nombre, "Tech Solutions")
        self.assertFalse(hasattr(result[0], "usuarios_empresa"))

    def test_search_service_trims_company_name(self):
        service = EmpresaService(Mock())
        service.repository = Mock()
        service.repository.search_by_name.return_value = [company(1, "Atanes")]

        result = service.search("  aTa  ")

        service.repository.search_by_name.assert_called_once_with("aTa")
        self.assertEqual(result[0].nombre, "Atanes")

    def test_current_user_companies_include_company_and_exact_role(self):
        service = EmpresaUsuarioService(Mock())
        service.repository = Mock()
        service.repository.get_by_usuario.return_value = [
            SimpleNamespace(empresa=company(1, "Owner Co"), rol=RolEmpresa.OWNER),
            SimpleNamespace(
                empresa=company(2, "Recruiter Co"), rol=RolEmpresa.RECRUITER
            ),
        ]

        result = service.get_by_current_user(25)

        service.repository.get_by_usuario.assert_called_once_with(25)
        self.assertEqual(result[0].rol, RolEmpresa.OWNER)
        self.assertEqual(result[1].rol, RolEmpresa.RECRUITER)

    def test_current_user_without_company_relations_returns_empty_list(self):
        service = EmpresaUsuarioService(Mock())
        service.repository = Mock()
        service.repository.get_by_usuario.return_value = []

        self.assertEqual(service.get_by_current_user(99), [])
        service.repository.get_by_usuario.assert_called_once_with(99)

    def test_my_companies_endpoint_uses_authenticated_user(self):
        user = SimpleNamespace(id=25)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: Mock()
        items = [
            MiEmpresaResponseDTO(
                empresa=EmpresaResponseDTO.model_validate(company(1, "Owner Co")),
                rol=RolEmpresa.OWNER,
            )
        ]
        try:
            with patch(
                "src.routers.empresa_router.EmpresaUsuarioService.get_by_current_user",
                return_value=items,
            ) as get_mine:
                response = TestClient(app).get("/api/empresas/me")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]["rol"], "OWNER")
            self.assertEqual(response.json()[0]["empresa"]["nombre"], "Owner Co")
            get_mine.assert_called_once_with(25)
        finally:
            app.dependency_overrides.clear()

    def test_company_search_endpoint_returns_matches(self):
        app.dependency_overrides[get_db] = lambda: Mock()
        matches = [EmpresaResponseDTO.model_validate(company(1, "Tech Solutions"))]
        try:
            with patch(
                "src.routers.empresa_router.EmpresaService.search",
                return_value=matches,
            ) as search:
                response = TestClient(app).get("/api/empresas?q=tech")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]["nombre"], "Tech Solutions")
            search.assert_called_once_with("tech")
        finally:
            app.dependency_overrides.clear()

    def test_company_search_rejects_blank_query(self):
        response = TestClient(app).get("/api/empresas?q=%20%20")
        self.assertEqual(response.status_code, 422)


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La prueba de búsqueda requiere la PostgreSQL configurada.",
)
class CompanyDiscoveryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def test_partial_case_insensitive_search_returns_the_real_company_id(self):
        marker = f"AtAnEs{uuid4().hex[:10]}"
        company_model = Empresa(nombre=f"Estudio {marker}", industria="Tecnología")
        self.db.add(company_model)
        self.db.commit()

        matches = EmpresaService(self.db).search(f"  {marker[2:-2].swapcase()}  ")

        self.assertIn(company_model.id, [company.id for company in matches])


if __name__ == "__main__":
    unittest.main()
