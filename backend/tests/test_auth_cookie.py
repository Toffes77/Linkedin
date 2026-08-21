import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jose import jwt
from starlette.requests import Request

from src.app import app
from src.config.env import settings
from src.dtos.auth_dto import LoginDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.auth_service import AuthService
from src.utils.errors import UnauthorizedError
from src.utils.hash import hash_password
from src.utils.jwt import ACCESS_TOKEN_EXPIRE_SECONDS, ALGORITHM, create_access_token


def request_with_cookie(token: str | None = None) -> Request:
    headers = [] if token is None else [(b"cookie", f"access_token={token}".encode())]
    return Request({"type": "http", "headers": headers})


class AuthenticationCookieTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(
            id=7,
            email="ana@example.com",
            nombre="Ana",
            headline="Backend developer",
            ciudad="Córdoba",
            foto_perfil_url=None,
            experiencias=[],
            password_hash=hash_password("Password123"),
        )

    def authenticate(self, *, credentials=None, token=None):
        repository = Mock()
        repository.get_by_id.return_value = self.user
        with patch(
            "src.middlewares.auth_middleware.UsuarioRepository",
            return_value=repository,
        ):
            return get_current_user(
                request=request_with_cookie(token),
                credentials=credentials,
                db=Mock(),
            )

    def test_login_service_accepts_valid_and_rejects_invalid_credentials(self):
        service = AuthService(Mock())
        service.repo = Mock()
        service.repo.get_by_email.return_value = self.user
        token = service.login(LoginDTO(email=self.user.email, password="Password123"))
        self.assertEqual(token.token_type, "bearer")
        self.assertTrue(token.access_token)

        with self.assertRaises(UnauthorizedError):
            service.login(LoginDTO(email=self.user.email, password="incorrecta"))

    def test_valid_bearer_still_authenticates(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=create_access_token({"sub": "7"})
        )
        self.assertEqual(self.authenticate(credentials=credentials).id, 7)

    def test_valid_cookie_authenticates_without_bearer(self):
        token = create_access_token({"sub": "7"})
        self.assertEqual(self.authenticate(token=token).id, 7)

    def test_bearer_takes_precedence_over_cookie(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=create_access_token({"sub": "7"})
        )
        self.assertEqual(self.authenticate(credentials=credentials, token="invalid").id, 7)

    def test_malformed_authorization_does_not_fall_back_to_cookie(self):
        token = create_access_token({"sub": "7"})
        request = Request(
            {
                "type": "http",
                "headers": [
                    (b"authorization", b"Basic invalid"),
                    (b"cookie", f"access_token={token}".encode()),
                ],
            }
        )
        with self.assertRaises(UnauthorizedError):
            get_current_user(request=request, credentials=None, db=Mock())

    def test_invalid_expired_or_missing_cookie_is_unauthorized(self):
        expired = jwt.encode(
            {"sub": "7", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
            settings.JWT_SECRET,
            algorithm=ALGORITHM,
        )
        for token in ("not-a-jwt", expired, None):
            with self.subTest(token=token), self.assertRaises(UnauthorizedError):
                self.authenticate(token=token)

    @patch("src.routers.auth_router.AuthService.login")
    def test_login_response_sets_persistent_httponly_cookie_and_keeps_token(self, login):
        token = create_access_token({"sub": "7"})
        login.return_value = SimpleNamespace(
            access_token=token,
            token_type="bearer",
            model_dump=lambda: {"access_token": token, "token_type": "bearer"},
        )
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": self.user.email, "password": "Password123"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], token)
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("access_token=", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn(f"max-age={ACCESS_TOKEN_EXPIRE_SECONDS}", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertIn("path=/", cookie)

    @patch("src.middlewares.auth_middleware.UsuarioRepository")
    def test_me_with_cookie_hides_password_and_logout_removes_session(self, repository_cls):
        repository = Mock()
        repository.get_by_id.return_value = self.user
        repository_cls.return_value = repository
        token = create_access_token({"sub": "7"})

        with patch("src.services.usuario_service.UsuarioRepository", return_value=repository):
            with TestClient(app) as client:
                client.cookies.set(
                    "access_token", token, domain="testserver.local", path="/"
                )
                me = client.get("/api/usuarios/me")
                self.assertEqual(me.status_code, 200)
                self.assertNotIn("password_hash", me.json())

                logout = client.post("/api/auth/logout")
                self.assertEqual(logout.status_code, 200)
                self.assertIn("access_token=", logout.headers["set-cookie"].lower())
                self.assertNotIn("access_token", client.cookies)

                after_logout = client.get("/api/usuarios/me")
                self.assertEqual(after_logout.status_code, 401)

    def test_me_without_session_is_unauthorized(self):
        with TestClient(app) as client:
            response = client.get("/api/usuarios/me")
        self.assertEqual(response.status_code, 401)

    def test_cors_allows_configured_frontend_with_credentials(self):
        with TestClient(app) as client:
            response = client.options(
                "/api/usuarios/me",
                headers={
                    "Origin": settings.FRONTEND_ORIGIN,
                    "Access-Control-Request-Method": "GET",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"], settings.FRONTEND_ORIGIN
        )
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")

    def test_existing_protected_routes_and_swagger_bearer_remain_available(self):
        paths = app.openapi()["paths"]
        self.assertIn("put", paths["/api/usuarios/me"])
        self.assertIn("put", paths["/api/usuarios/me/password"])
        self.assertIn("put", paths["/api/usuarios/me/foto-perfil"])
        self.assertIn("HTTPBearer", app.openapi()["components"]["securitySchemes"])


if __name__ == "__main__":
    unittest.main()
