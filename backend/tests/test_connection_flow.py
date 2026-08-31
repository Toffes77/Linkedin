import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.app import app
from src.db.connection import get_db
from src.dtos.conexiones_dto import (
    CreateConexionDTO,
    EstadoConexionResponseDTO,
    UpdateConexionDTO,
)
from src.middlewares.auth_middleware import get_current_user
from src.services.conexion_service import ConexionService
from src.utils.errors import ConflictError


def user(user_id: int, nombre: str = "Usuario"):
    return SimpleNamespace(id=user_id, nombre=nombre)


def connection(
    usuario_a: int,
    usuario_b: int,
    estado: str = "pendiente",
    solicitante_id: int | None = None,
):
    return SimpleNamespace(
        usuario_a=usuario_a,
        usuario_b=usuario_b,
        solicitante_id=solicitante_id or usuario_a,
        fecha=datetime.now(),
        estado=estado,
    )


class ConnectionFlowTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()

    def tearDown(self):
        app.dependency_overrides.clear()

    def service_with_connection(self, existing):
        service = ConexionService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(2)
        service.repository = Mock()
        service.repository.get_by_usuarios.return_value = existing
        return service

    def test_connection_status_distinguishes_absent_sent_received_and_accepted(self):
        cases = [
            (None, 1, 2, "SIN_CONEXION"),
            (connection(1, 2), 1, 2, "PENDIENTE_ENVIADA"),
            (connection(1, 2), 2, 1, "PENDIENTE_RECIBIDA"),
            (connection(1, 2, "aceptada"), 1, 2, "CONECTADO"),
            (connection(1, 2, "aceptada"), 2, 1, "CONECTADO"),
        ]

        for existing, current_user_id, profile_id, expected in cases:
            with self.subTest(expected=expected, current_user_id=current_user_id):
                result = self.service_with_connection(existing).get_estado(
                    current_user_id,
                    profile_id,
                )
                self.assertEqual(result.estado, expected)

    def test_status_endpoint_is_authenticated_and_uses_current_user_direction(self):
        expected = EstadoConexionResponseDTO(
            estado="PENDIENTE_RECIBIDA",
            usuario_a=4,
            usuario_b=9,
        )
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: user(9)
        with patch(
            "src.routers.conexion_router.ConexionService.get_estado",
            return_value=expected,
        ) as get_status:
            response = TestClient(app).get("/api/conexiones/estado/4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected.model_dump())
        get_status.assert_called_once_with(9, 4)

    def test_status_endpoint_requires_a_session(self):
        response = TestClient(app).get("/api/conexiones/estado/4")
        self.assertEqual(response.status_code, 401)

    def test_new_connection_and_notification_share_one_commit(self):
        db = Mock()
        service = ConexionService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.side_effect = lambda user_id: {
            1: user(1, "Juan Cruz"),
            2: user(2, "Pedro"),
        }.get(user_id)
        service.repository = Mock()
        service.repository.get_by_usuarios.return_value = None
        created = connection(1, 2)
        service.repository.create.return_value = created
        service.notificacion_service = Mock()

        result = service.create(CreateConexionDTO(usuario_a=1, usuario_b=2), 1)

        service.repository.create.assert_called_once_with(
            CreateConexionDTO(usuario_a=1, usuario_b=2, solicitante_id=1),
            commit=False,
        )
        notifications = service.notificacion_service.create_many.call_args.args[0]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].tipo, "NUEVA_INVITACION_CONEXION")
        self.assertEqual(notifications[0].usuario_id, 2)
        self.assertEqual(notifications[0].usuario_origen_id, 1)
        self.assertEqual(notifications[0].mensaje, "Juan Cruz quiere conectar con vos.")
        service.notificacion_service.create_many.assert_called_once_with(
            notifications,
            commit=False,
        )
        db.commit.assert_called_once_with()
        db.refresh.assert_called_once_with(created)
        db.rollback.assert_not_called()
        self.assertEqual(result.estado, "pendiente")

    def test_existing_connection_does_not_create_another_notification(self):
        service = self.service_with_connection(connection(1, 2))
        service.notificacion_service = Mock()

        with self.assertRaises(ConflictError):
            service.create(CreateConexionDTO(usuario_a=1, usuario_b=2), 1)

        service.repository.create.assert_not_called()
        service.notificacion_service.create_many.assert_not_called()

    def test_notification_failure_rolls_back_new_connection(self):
        db = Mock()
        service = ConexionService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.side_effect = lambda user_id: user(user_id)
        service.repository = Mock()
        service.repository.get_by_usuarios.return_value = None
        service.repository.create.return_value = connection(1, 2)
        service.notificacion_service = Mock()
        service.notificacion_service.create_many.side_effect = RuntimeError(
            "forced notification failure"
        )

        with self.assertRaisesRegex(RuntimeError, "forced notification failure"):
            service.create(CreateConexionDTO(usuario_a=1, usuario_b=2), 1)

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()

    def test_acceptance_notifies_original_sender_with_one_commit(self):
        db = Mock()
        service = ConexionService(db)
        pending = connection(1, 2)
        service.repository = Mock()
        service.repository.get_by_id.return_value = pending
        service.repository.update.return_value = pending
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(2, "Pedro Gómez")
        service.notificacion_service = Mock()

        result = service.update(
            1,
            2,
            UpdateConexionDTO(estado="aceptada"),
            usuario_autenticado_id=2,
        )

        service.repository.update.assert_called_once_with(
            pending,
            UpdateConexionDTO(estado="aceptada"),
            commit=False,
        )
        notifications = service.notificacion_service.create_many.call_args.args[0]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].usuario_id, 1)
        self.assertEqual(notifications[0].usuario_origen_id, 2)
        self.assertEqual(notifications[0].tipo, "CONEXION_ACEPTADA")
        self.assertEqual(
            notifications[0].mensaje,
            "Pedro Gómez aceptó tu solicitud de conexión.",
        )
        service.notificacion_service.create_many.assert_called_once_with(
            notifications,
            commit=False,
        )
        db.commit.assert_called_once_with()
        db.refresh.assert_called_once_with(pending)
        db.rollback.assert_not_called()
        self.assertEqual(result.usuario_a, 1)
        self.assertEqual(result.usuario_b, 2)

    def test_rejection_does_not_create_acceptance_notification(self):
        service = ConexionService(Mock())
        pending = connection(1, 2)
        rejected = connection(1, 2, "rechazada")
        service.repository = Mock()
        service.repository.get_by_id.return_value = pending
        service.repository.update.return_value = rejected
        service.notificacion_service = Mock()

        result = service.update(
            1,
            2,
            UpdateConexionDTO(estado="rechazada"),
            usuario_autenticado_id=2,
        )

        service.repository.update.assert_called_once_with(
            pending,
            UpdateConexionDTO(estado="rechazada"),
        )
        service.notificacion_service.create_many.assert_not_called()
        self.assertEqual(result.estado, "rechazada")

    def test_repeated_acceptance_does_not_create_another_notification(self):
        service = ConexionService(Mock())
        service.repository = Mock()
        service.repository.get_by_id.return_value = connection(1, 2, "aceptada")
        service.notificacion_service = Mock()

        with self.assertRaises(ConflictError):
            service.update(
                1,
                2,
                UpdateConexionDTO(estado="aceptada"),
                usuario_autenticado_id=2,
            )

        service.repository.update.assert_not_called()
        service.notificacion_service.create_many.assert_not_called()

    def test_notification_failure_rolls_back_acceptance(self):
        db = Mock()
        service = ConexionService(db)
        pending = connection(1, 2)
        service.repository = Mock()
        service.repository.get_by_id.return_value = pending
        service.repository.update.return_value = pending
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(2, "Pedro")
        service.notificacion_service = Mock()
        service.notificacion_service.create_many.side_effect = RuntimeError(
            "forced acceptance notification failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "forced acceptance notification failure",
        ):
            service.update(
                1,
                2,
                UpdateConexionDTO(estado="aceptada"),
                usuario_autenticado_id=2,
            )

        service.repository.update.assert_called_once_with(
            pending,
            UpdateConexionDTO(estado="aceptada"),
            commit=False,
        )
        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
