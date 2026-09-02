import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.app import app
from src.db.connection import SessionLocal, engine, get_db
from src.db.models.empresa_usuario_model import (
    EMPRESA_USUARIO_UNIQUE_CONSTRAINT,
    RolEmpresa,
)
from src.db.models.postulacion_model import POSTULACION_UNIQUE_CONSTRAINT
from src.db.models.reaciones_model import REACCIONES_UNIQUE_CONSTRAINT
from src.db.models.seguimiento_model import SEGUIMIENTO_UNIQUE_CONSTRAINT
from src.db.models.seguimiento_model import Seguimiento
from src.db.models.usuario_model import Usuario
from src.dtos.empresa_usuario_dto import CreateEmpresaUsuarioDTO
from src.dtos.postulacion_dto import CreatePostulacionDTO
from src.dtos.reacciones_dto import CreateReaccionDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.empresa_usuario_service import EmpresaUsuarioService
from src.services.postulacion_service import PostulacionService
from src.services.reacciones_service import ReaccionesService
from src.services.seguimiento_service import SeguimientoService
from src.utils.errors import ConflictError


def integrity_error(constraint_name: str) -> IntegrityError:
    original = RuntimeError("internal database detail")
    original.diag = SimpleNamespace(constraint_name=constraint_name)
    return IntegrityError("INSERT INTO internal_table", {}, original)


def user(user_id: int, name: str = "User"):
    return SimpleNamespace(id=user_id, nombre=name)


class KnownIntegrityConflictServiceTests(unittest.TestCase):
    def test_application_unique_violation_rolls_back_and_becomes_conflict(self):
        db = Mock()
        service = PostulacionService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(2, "Candidate")
        service.oferta_repository = Mock()
        service.oferta_repository.get_by_id.return_value = SimpleNamespace(
            id=3,
            empresa_id=4,
            titulo="Backend",
            publicada=True,
        )
        service.repository = Mock()
        service.repository.get_by_oferta_and_usuario.return_value = None
        service.repository.create.side_effect = integrity_error(
            POSTULACION_UNIQUE_CONSTRAINT
        )

        with self.assertRaisesRegex(ConflictError, "ya se postuló"):
            service.create(CreatePostulacionDTO(oferta_id=3, usuario_id=2))

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()

    def test_follow_unique_violation_rolls_back_and_becomes_conflict(self):
        db = Mock()
        service = SeguimientoService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.side_effect = lambda user_id: user(user_id)
        service.repository = Mock()
        service.repository.get.return_value = None
        service.repository.create.side_effect = integrity_error(
            SEGUIMIENTO_UNIQUE_CONSTRAINT
        )

        with self.assertRaisesRegex(ConflictError, "Ya sigue"):
            service.follow(1, 2)

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()

    def test_reaction_unique_violation_rolls_back_and_becomes_conflict(self):
        db = Mock()
        service = ReaccionesService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(1)
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_by_id.return_value = SimpleNamespace(id=3)
        service.repository = Mock()
        service.repository.get_by_usuario_and_publicacion.return_value = None
        service.repository.create.side_effect = integrity_error(
            REACCIONES_UNIQUE_CONSTRAINT
        )

        with self.assertRaisesRegex(ConflictError, "ya reaccionó"):
            service.create(
                CreateReaccionDTO(
                    usuario_id=1,
                    publicacion_id=3,
                    tipo="like",
                )
            )

        db.rollback.assert_called_once_with()

    def test_membership_unique_violation_rolls_back_and_becomes_conflict(self):
        db = Mock()
        service = EmpresaUsuarioService(db)
        service.empresa_repository = Mock()
        service.empresa_repository.get_by_id.return_value = SimpleNamespace(id=4)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(2)
        service.repository = Mock()
        service.repository.has_any_role.return_value = True
        service.repository.get_by_empresa_and_usuario.return_value = None
        service.repository.create.side_effect = integrity_error(
            EMPRESA_USUARIO_UNIQUE_CONSTRAINT
        )

        with self.assertRaisesRegex(ConflictError, "ya pertenece"):
            service.create(
                4,
                CreateEmpresaUsuarioDTO(
                    usuario_id=2,
                    rol=RolEmpresa.COLLABORATOR,
                ),
                usuario_actual_id=1,
            )

        db.rollback.assert_called_once_with()

    def test_unknown_integrity_error_rolls_back_and_is_not_mapped_to_conflict(self):
        db = Mock()
        service = ReaccionesService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(1)
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_by_id.return_value = SimpleNamespace(id=3)
        service.repository = Mock()
        service.repository.get_by_usuario_and_publicacion.return_value = None
        unknown = integrity_error("unexpected_foreign_key")
        service.repository.create.side_effect = unknown

        with self.assertRaises(IntegrityError) as raised:
            service.create(
                CreateReaccionDTO(
                    usuario_id=1,
                    publicacion_id=3,
                    tipo="like",
                )
            )

        self.assertIs(raised.exception, unknown)
        db.rollback.assert_called_once_with()


class KnownIntegrityConflictEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.current_user = user(1, "Authenticated")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def assert_safe_conflict(self, response, expected_message: str):
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn(expected_message, response.json()["message"])
        for internal_detail in (
            "INSERT INTO",
            "constraint",
            "pkey",
            "internal_table",
            "PostgreSQL",
        ):
            self.assertNotIn(internal_detail, response.text)

    def test_application_race_path_returns_safe_409(self):
        offer = SimpleNamespace(
            id=3,
            empresa_id=4,
            titulo="Backend",
            publicada=True,
        )
        with (
            patch(
                "src.repositories.usuario_repository.UsuarioRepository.get_by_id",
                return_value=user(1),
            ),
            patch(
                "src.repositories.oferta_repository.OfertaRepository.get_by_id",
                return_value=offer,
            ),
            patch(
                "src.repositories.postulacion_repository.PostulacionRepository.get_by_oferta_and_usuario",
                return_value=None,
            ),
            patch(
                "src.repositories.postulacion_repository.PostulacionRepository.create",
                side_effect=integrity_error(POSTULACION_UNIQUE_CONSTRAINT),
            ),
        ):
            response = self.client.post(
                "/api/postulaciones",
                json={"oferta_id": 3, "usuario_id": 999},
            )

        self.assert_safe_conflict(response, "ya se postuló")
        self.db.rollback.assert_called_once_with()

    def test_follow_race_path_returns_safe_409(self):
        with (
            patch(
                "src.repositories.usuario_repository.UsuarioRepository.get_by_id",
                side_effect=lambda user_id: user(user_id),
            ),
            patch(
                "src.repositories.seguimiento_repository.SeguimientoRepository.get",
                return_value=None,
            ),
            patch(
                "src.repositories.seguimiento_repository.SeguimientoRepository.create",
                side_effect=integrity_error(SEGUIMIENTO_UNIQUE_CONSTRAINT),
            ),
        ):
            response = self.client.post("/api/usuarios/2/seguir")

        self.assert_safe_conflict(response, "Ya sigue")
        self.db.rollback.assert_called_once_with()

    def test_reaction_race_path_returns_safe_409(self):
        with (
            patch(
                "src.repositories.usuario_repository.UsuarioRepository.get_by_id",
                return_value=user(1),
            ),
            patch(
                "src.repositories.publicacion_repository.PublicacionRepository.get_by_id",
                return_value=SimpleNamespace(id=3),
            ),
            patch(
                "src.repositories.reacciones_repository.ReaccionRepository.get_by_usuario_and_publicacion",
                return_value=None,
            ),
            patch(
                "src.repositories.reacciones_repository.ReaccionRepository.create",
                side_effect=integrity_error(REACCIONES_UNIQUE_CONSTRAINT),
            ),
        ):
            response = self.client.post(
                "/api/reacciones",
                json={"publicacion_id": 3, "tipo": "like"},
            )

        self.assert_safe_conflict(response, "ya reaccionó")
        self.db.rollback.assert_called_once_with()

    def test_membership_race_path_returns_safe_409(self):
        with (
            patch(
                "src.repositories.empresa_repository.EmpresaRepository.get_by_id",
                return_value=SimpleNamespace(id=4),
            ),
            patch(
                "src.repositories.usuario_repository.UsuarioRepository.get_by_id",
                return_value=user(2),
            ),
            patch(
                "src.repositories.empresa_usuario_repository.EmpresaUsuarioRepository.has_any_role",
                return_value=True,
            ),
            patch(
                "src.repositories.empresa_usuario_repository.EmpresaUsuarioRepository.get_by_empresa_and_usuario",
                return_value=None,
            ),
            patch(
                "src.repositories.empresa_usuario_repository.EmpresaUsuarioRepository.create",
                side_effect=integrity_error(EMPRESA_USUARIO_UNIQUE_CONSTRAINT),
            ),
        ):
            response = self.client.post(
                "/api/empresas/4/usuarios",
                json={"usuario_id": 2, "rol": "COLLABORATOR"},
            )

        self.assert_safe_conflict(response, "ya pertenece")
        self.db.rollback.assert_called_once_with()


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La recuperación real de la sesión requiere la PostgreSQL configurada.",
)
class FollowIntegrityRollbackPostgresTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        with SessionLocal() as db:
            follower = Usuario(
                email=f"follow-rollback-a-{suffix}@example.com",
                nombre="Follower",
                password_hash="not-used",
                headline="Test",
                ciudad="Buenos Aires",
            )
            followed = Usuario(
                email=f"follow-rollback-b-{suffix}@example.com",
                nombre="Followed",
                password_hash="not-used",
                headline="Test",
                ciudad="Buenos Aires",
            )
            db.add_all([follower, followed])
            db.flush()
            self.follower_id = follower.id
            self.followed_id = followed.id
            db.add(
                Seguimiento(
                    seguidor_id=self.follower_id,
                    seguido_id=self.followed_id,
                )
            )
            db.commit()

    def tearDown(self):
        with SessionLocal() as db:
            db.query(Seguimiento).filter(
                Seguimiento.seguidor_id == self.follower_id,
                Seguimiento.seguido_id == self.followed_id,
            ).delete(synchronize_session=False)
            db.query(Usuario).filter(
                Usuario.id.in_((self.follower_id, self.followed_id))
            ).delete(synchronize_session=False)
            db.commit()

    def test_known_database_violation_rolls_back_and_session_remains_usable(self):
        with SessionLocal() as db:
            service = SeguimientoService(db)
            service.repository.get = Mock(return_value=None)

            with self.assertRaisesRegex(ConflictError, "Ya sigue"):
                service.follow(self.follower_id, self.followed_id)

            self.assertEqual(db.execute(text("SELECT 1")).scalar_one(), 1)
            self.assertIsNotNone(
                db.get(Seguimiento, (self.follower_id, self.followed_id))
            )


if __name__ == "__main__":
    unittest.main()
