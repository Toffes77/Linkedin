import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pydantic import ValidationError
from fastapi.security import HTTPAuthorizationCredentials

from src.dtos.usuario_dto import UpdatePasswordDTO, UpdateUsuarioDTO
from src.middlewares.auth_middleware import get_current_user
from src.schemas.usuario_schema import UpdatePasswordSchema, UpdateUsuarioSchema
from src.services.usuario_service import UsuarioService
from src.utils.errors import BadRequestError, UnauthorizedError
from src.utils.hash import hash_password, verify_password


class FakeUsuarioRepository:
    def __init__(self, usuario):
        self.usuario = usuario
        self.requested_id = None
        self.updated = False

    def get_by_id(self, usuario_id: int):
        self.requested_id = usuario_id
        return self.usuario if usuario_id == self.usuario.id else None

    def update_password_hash(self, usuario, password_hash: str):
        usuario.password_hash = password_hash
        self.updated = True
        return usuario

    def update_profile(self, usuario, usuario_data: UpdateUsuarioDTO):
        if usuario_data.nombre is not None:
            usuario.nombre = usuario_data.nombre
        if usuario_data.headline is not None:
            usuario.headline = usuario_data.headline
        if usuario_data.ciudad is not None:
            usuario.ciudad = usuario_data.ciudad
        self.updated = True
        return usuario


class PasswordChangeTests(unittest.TestCase):
    def setUp(self):
        self.usuario = SimpleNamespace(
            id=15,
            email="usuario@example.com",
            nombre="Usuario",
            headline="Desarrollador",
            ciudad="Buenos Aires",
            password_hash=hash_password("PasswordActual123"),
            foto_perfil_url="/imagenes/usuario_15.png",
            experiencias=[],
        )
        self.repository = FakeUsuarioRepository(self.usuario)
        self.service = UsuarioService(None)
        self.service.repository = self.repository

    def test_changes_only_authenticated_users_password_and_hashes_it(self):
        previous_email = self.usuario.email
        previous_name = self.usuario.nombre

        response = self.service.update_password(
            15,
            UpdatePasswordDTO(
                password_actual="PasswordActual123",
                password_nueva="PasswordNueva456",
            ),
        )

        self.assertEqual(response.message, "Contrase\u00f1a actualizada correctamente")
        self.assertEqual(self.repository.requested_id, 15)
        self.assertTrue(self.repository.updated)
        self.assertTrue(verify_password("PasswordNueva456", self.usuario.password_hash))
        self.assertFalse(verify_password("PasswordActual123", self.usuario.password_hash))
        self.assertNotEqual(self.usuario.password_hash, "PasswordNueva456")
        self.assertEqual(self.usuario.email, previous_email)
        self.assertEqual(self.usuario.nombre, previous_name)

    def test_rejects_an_incorrect_current_password(self):
        with self.assertRaises(UnauthorizedError):
            self.service.update_password(
                15,
                UpdatePasswordDTO(
                    password_actual="Incorrecta123",
                    password_nueva="PasswordNueva456",
                ),
            )
        self.assertFalse(self.repository.updated)

    def test_rejects_the_same_new_password(self):
        with self.assertRaises(BadRequestError):
            self.service.update_password(
                15,
                UpdatePasswordDTO(
                    password_actual="PasswordActual123",
                    password_nueva="PasswordActual123",
                ),
            )
        self.assertFalse(self.repository.updated)

    def test_rejects_a_new_password_shorter_than_registration_rule(self):
        with self.assertRaises(ValidationError):
            UpdatePasswordSchema(
                password_actual="PasswordActual123",
                password_nueva="corta",
            )

    def test_missing_jwt_is_unauthorized(self):
        with self.assertRaises(UnauthorizedError):
            get_current_user(credentials=None, db=Mock())

    def test_invalid_jwt_is_unauthorized(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="token-invalido",
        )
        with self.assertRaises(UnauthorizedError):
            get_current_user(credentials=credentials, db=Mock())

    def test_updates_only_allowed_profile_fields(self):
        previous_hash = self.usuario.password_hash
        previous_email = self.usuario.email
        previous_photo = self.usuario.foto_perfil_url

        response = self.service.update_profile(
            15,
            UpdateUsuarioDTO(
                nombre="Nombre actualizado",
                headline="Headline actualizado",
                ciudad="Cordoba",
            ),
        )

        self.assertEqual(response.nombre, "Nombre actualizado")
        self.assertEqual(response.headline, "Headline actualizado")
        self.assertEqual(response.ciudad, "Cordoba")
        self.assertEqual(self.usuario.password_hash, previous_hash)
        self.assertEqual(self.usuario.email, previous_email)
        self.assertEqual(self.usuario.foto_perfil_url, previous_photo)

    def test_profile_schema_rejects_sensitive_or_unauthorized_fields(self):
        for field, value in (
            ("password", "PasswordNueva456"),
            ("password_hash", "hash-ajeno"),
            ("email", "otro@example.com"),
            ("foto_perfil_url", "/imagenes/ajena.png"),
            ("id", 999),
        ):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                UpdateUsuarioSchema(nombre="Nombre", **{field: value})


if __name__ == "__main__":
    unittest.main()
