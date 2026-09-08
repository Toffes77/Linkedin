import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.usuario_model import Usuario
from src.dtos.usuario_dto import CreateUsuarioDTO, UpdateUsuarioDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.ubicacion_service import UbicacionService
from src.services.usuario_service import UsuarioService
from src.utils.errors import BadRequestError


class CityCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_buenos_search_returns_canonical_city(self):
        response = self.client.get(
            "/api/ubicaciones/ciudades",
            params={"q": "buenos"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["nombre"], "Argentina, Buenos Aires")

    def test_search_is_case_and_accent_insensitive(self):
        uppercase = self.client.get(
            "/api/ubicaciones/ciudades",
            params={"q": "BUENOS"},
        )
        without_accent = self.client.get(
            "/api/ubicaciones/ciudades",
            params={"q": "cordoba"},
        )

        self.assertEqual(uppercase.status_code, 200)
        self.assertEqual(uppercase.json()[0]["nombre"], "Argentina, Buenos Aires")
        self.assertIn(
            "Argentina, Córdoba",
            [city["nombre"] for city in without_accent.json()],
        )

    def test_short_query_and_invalid_limits_are_controlled(self):
        self.assertEqual(
            self.client.get("/api/ubicaciones/ciudades", params={"q": "b"}).status_code,
            422,
        )
        maximum = self.client.get(
            "/api/ubicaciones/ciudades",
            params={"q": "san", "limit": 15},
        )
        self.assertEqual(maximum.status_code, 200)
        self.assertLessEqual(len(maximum.json()), 15)
        self.assertEqual(
            self.client.get(
                "/api/ubicaciones/ciudades",
                params={"q": "buenos", "limit": 16},
            ).status_code,
            422,
        )

    def test_limit_is_respected_and_response_has_expected_format(self):
        response = self.client.get(
            "/api/ubicaciones/ciudades",
            params={"q": "san", "limit": 3},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)
        for city in response.json():
            self.assertEqual(city["nombre"], f"{city['pais']}, {city['ciudad']}")

    def test_no_results_returns_empty_list(self):
        response = self.client.get(
            "/api/ubicaciones/ciudades",
            params={"q": "ciudad-inexistente-xyz"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_spanish_country_and_city_names_are_preserved(self):
        result = UbicacionService().search_cities("paris", 1)

        self.assertEqual(result[0].pais, "Francia")
        self.assertEqual(result[0].ciudad, "París")
        self.assertEqual(result[0].nombre, "Francia, París")


class FakeUsuarioRepository:
    def __init__(self, existing: Usuario | None = None):
        self.existing = existing
        self.created: Usuario | None = None
        self.updated = False

    def get_by_email(self, email: str):
        return None

    def create(self, usuario: Usuario):
        usuario.id = 901
        self.created = usuario
        return usuario

    def get_by_id(self, usuario_id: int):
        if self.existing is not None and self.existing.id == usuario_id:
            return self.existing
        return None

    def update_profile(self, usuario: Usuario, data: UpdateUsuarioDTO):
        if data.nombre is not None:
            usuario.nombre = data.nombre
        if data.headline is not None:
            usuario.headline = data.headline
        if data.ciudad is not None:
            usuario.ciudad = data.ciudad
        self.updated = True
        return usuario


def create_dto(city: str) -> CreateUsuarioDTO:
    return CreateUsuarioDTO(
        email="city-user@example.com",
        password="Password123",
        nombre="City User",
        headline="Ingeniería",
        ciudad=city,
        acepta_terminos=True,
    )


class UserCityValidationTests(unittest.TestCase):
    def service_with(self, repository: FakeUsuarioRepository) -> UsuarioService:
        service = UsuarioService(Mock())
        service.repository = repository
        return service

    def test_registration_accepts_and_canonicalizes_catalog_city(self):
        repository = FakeUsuarioRepository()

        created = self.service_with(repository).create(
            create_dto("argentina, buenos aires")
        )

        self.assertEqual(created.ciudad, "Argentina, Buenos Aires")
        self.assertEqual(repository.created.ciudad, "Argentina, Buenos Aires")

    def test_registration_rejects_invented_city_without_persisting(self):
        repository = FakeUsuarioRepository()

        with self.assertRaises(BadRequestError):
            self.service_with(repository).create(
                create_dto("Planeta Marte, Ciudad Pepe")
            )

        self.assertIsNone(repository.created)

    def test_profile_update_accepts_and_canonicalizes_catalog_city(self):
        user = Usuario(
            id=902,
            email="existing@example.com",
            password_hash="unused",
            nombre="Existing",
            headline="Engineering",
            ciudad="Argentina, Rosario",
        )
        repository = FakeUsuarioRepository(user)

        updated = self.service_with(repository).update_profile(
            user.id,
            UpdateUsuarioDTO(ciudad="francia, paris"),
        )

        self.assertEqual(updated.ciudad, "Francia, París")
        self.assertTrue(repository.updated)

    def test_profile_update_rejects_invented_city_without_persisting(self):
        user = Usuario(
            id=903,
            email="existing-2@example.com",
            password_hash="unused",
            nombre="Existing",
            headline="Engineering",
            ciudad="Argentina, Rosario",
        )
        repository = FakeUsuarioRepository(user)

        with self.assertRaises(BadRequestError):
            self.service_with(repository).update_profile(
                user.id,
                UpdateUsuarioDTO(ciudad="Argentina, Ciudad Inventada XYZ"),
            )

        self.assertFalse(repository.updated)
        self.assertEqual(user.ciudad, "Argentina, Rosario")

    def test_existing_legacy_city_is_not_modified_when_other_fields_change(self):
        user = Usuario(
            id=904,
            email="legacy@example.com",
            password_hash="unused",
            nombre="Legacy",
            headline="Previous headline",
            ciudad="Ciudad heredada",
        )
        repository = FakeUsuarioRepository(user)

        updated = self.service_with(repository).update_profile(
            user.id,
            UpdateUsuarioDTO(headline="Nuevo headline"),
        )

        self.assertEqual(updated.ciudad, "Ciudad heredada")
        self.assertEqual(updated.headline, "Nuevo headline")


class UserCityApiTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: Mock()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_registration_contract_accepts_valid_and_rejects_invented_city(self):
        repository = FakeUsuarioRepository()
        payload = {
            **create_dto("Argentina, Buenos Aires").model_dump(mode="json"),
            "acepta_terminos": True,
        }

        with patch(
            "src.services.usuario_service.UsuarioRepository",
            return_value=repository,
        ):
            valid = self.client.post("/api/usuarios", json=payload)
            invalid = self.client.post(
                "/api/usuarios",
                json={**payload, "email": "other@example.com", "ciudad": "Marte, Pepe"},
            )

        self.assertEqual(valid.status_code, 201, valid.text)
        self.assertEqual(valid.json()["ciudad"], "Argentina, Buenos Aires")
        self.assertEqual(invalid.status_code, 400, invalid.text)

    def test_profile_update_contract_accepts_valid_and_rejects_invented_city(self):
        user = Usuario(
            id=905,
            email="profile-city@example.com",
            password_hash="unused",
            nombre="Profile City",
            headline="Engineering",
            ciudad="Argentina, Rosario",
        )
        repository = FakeUsuarioRepository(user)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user.id)

        with patch(
            "src.services.usuario_service.UsuarioRepository",
            return_value=repository,
        ):
            valid = self.client.put(
                "/api/usuarios/me",
                json={"ciudad": "alemania, berlin"},
            )
            invalid = self.client.put(
                "/api/usuarios/me",
                json={"ciudad": "Marte, Pepe"},
            )

        self.assertEqual(valid.status_code, 200, valid.text)
        self.assertEqual(valid.json()["ciudad"], "Alemania, Berlín")
        self.assertEqual(invalid.status_code, 400, invalid.text)
        self.assertEqual(user.ciudad, "Alemania, Berlín")


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Esta regresión de persistencia requiere PostgreSQL.",
)
class UserCityPostgreSQLIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def test_selected_city_is_persisted_and_invented_city_is_not(self):
        suffix = uuid4().hex
        selected_email = f"city-selected-{suffix}@example.com"
        invented_email = f"city-invented-{suffix}@example.com"
        payload = {
            **create_dto("Argentina, Buenos Aires").model_dump(mode="json"),
            "acepta_terminos": True,
        }

        selected = self.client.post(
            "/api/usuarios",
            json={**payload, "email": selected_email},
        )
        invented = self.client.post(
            "/api/usuarios",
            json={
                **payload,
                "email": invented_email,
                "ciudad": "Planeta Marte, Ciudad Pepe",
            },
        )

        self.assertEqual(selected.status_code, 201, selected.text)
        self.assertEqual(invented.status_code, 400, invented.text)
        stored = self.db.query(Usuario).filter(
            func.lower(Usuario.email) == selected_email
        ).one()
        self.assertEqual(stored.ciudad, "Argentina, Buenos Aires")
        self.assertEqual(
            self.db.query(Usuario).filter(
                func.lower(Usuario.email) == invented_email
            ).count(),
            0,
        )


if __name__ == "__main__":
    unittest.main()
