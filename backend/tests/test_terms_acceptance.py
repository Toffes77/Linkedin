import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.app import app
from src.db.connection import get_db
from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import CreateUsuarioDTO, UsuarioResponseDTO
from src.schemas.usuario_schema import CreateUsuarioSchema


BASE_PAYLOAD = {
    "email": "terms@example.com",
    "password": "password-123",
    "nombre": "Terms User",
    "headline": "Proyecto educativo",
    "ciudad": "Argentina, Buenos Aires",
}


class TermsAcceptanceSchemaTests(unittest.TestCase):
    def test_acceptance_is_required_and_must_be_true(self):
        valid = CreateUsuarioSchema(**BASE_PAYLOAD, acepta_terminos=True)
        self.assertTrue(valid.acepta_terminos)
        self.assertTrue(CreateUsuarioSchema.model_fields["acepta_terminos"].is_required())

        with self.assertRaises(ValidationError):
            CreateUsuarioSchema(**BASE_PAYLOAD, acepta_terminos=False)
        with self.assertRaises(ValidationError):
            CreateUsuarioSchema(**BASE_PAYLOAD)


class TermsAcceptanceApiTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: Mock()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_endpoint_rejects_false_and_missing_acceptance(self):
        false_response = self.client.post(
            "/api/usuarios",
            json={**BASE_PAYLOAD, "acepta_terminos": False},
        )
        missing_response = self.client.post("/api/usuarios", json=BASE_PAYLOAD)

        self.assertEqual(false_response.status_code, 422)
        self.assertEqual(missing_response.status_code, 422)

    @patch("src.routers.usuario_router.UsuarioService.create")
    def test_true_is_accepted_and_discarded_before_domain_persistence(self, create):
        create.return_value = UsuarioResponseDTO(
            id=901,
            nombre="Terms User",
            headline="Proyecto educativo",
            ciudad="Argentina, Buenos Aires",
            foto_perfil_url=None,
            experiencias=[],
        )

        response = self.client.post(
            "/api/usuarios",
            json={**BASE_PAYLOAD, "acepta_terminos": True},
        )

        self.assertEqual(response.status_code, 201, response.text)
        create.assert_called_once()
        dto = create.call_args.args[0]
        self.assertIsInstance(dto, CreateUsuarioDTO)
        self.assertNotIn("acepta_terminos", dto.model_dump())
        self.assertNotIn("acepta_terminos", CreateUsuarioDTO.model_fields)
        self.assertNotIn("acepta_terminos", Usuario.__table__.columns)

    def test_openapi_documents_required_non_persisted_acceptance(self):
        operation = app.openapi()["paths"]["/api/usuarios"]["post"]
        schema_name = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
        schema = app.openapi()["components"]["schemas"][schema_name]

        self.assertIn("acepta_terminos", schema["required"])
        self.assertIn("acepta_terminos", schema["properties"])
        self.assertIn("no se persiste", schema["properties"]["acepta_terminos"]["description"])
        self.assertIn("no se persiste", operation["description"])


if __name__ == "__main__":
    unittest.main()
