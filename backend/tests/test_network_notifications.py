import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.app import app
from src.db.connection import get_db
from src.dtos.conexiones_dto import InvitacionRecibidaResponseDTO
from src.dtos.notificacion_dto import NotificacionResponseDTO
from src.dtos.postulacion_dto import CreatePostulacionDTO, PostulacionResponseDTO, UpdatePostulacionDTO
from src.dtos.usuario_dto import UsuarioResponseDTO
from src.mappers.postulacion_mapper import PostulacionMapper
from src.middlewares.auth_middleware import get_current_user
from src.services.notificacion_service import NotificacionService
from src.services.postulacion_service import PostulacionService
from src.utils.errors import ConflictError, ForbiddenError


def user(user_id: int, name: str = "Juan"):
    return SimpleNamespace(
        id=user_id,
        nombre=name,
        headline="Desarrollador",
        ciudad="Buenos Aires",
        foto_perfil_url=None,
        experiencias=[],
    )


class NetworkNotificationsTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_received_invitations_endpoint_returns_pending_sender_data(self):
        invitation = InvitacionRecibidaResponseDTO(
            usuario_a=4,
            usuario_b=9,
            fecha=datetime.now(),
            estado="pendiente",
            usuario=UsuarioResponseDTO.model_validate(user(4, "Ana")),
        )
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: user(9)
        with patch(
            "src.routers.conexion_router.ConexionService.get_invitaciones_recibidas",
            return_value=[invitation],
        ) as get_received:
            response = TestClient(app).get("/api/conexiones/invitaciones-recibidas")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["usuario"]["nombre"], "Ana")
        get_received.assert_called_once_with(9)

    def test_received_invitations_requires_a_session(self):
        response = TestClient(app).get("/api/conexiones/invitaciones-recibidas")
        self.assertEqual(response.status_code, 401)

    def test_notification_list_and_unread_count_are_scoped_to_current_user(self):
        notification = NotificacionResponseDTO(
            id=1, usuario_id=9, tipo="POSTULACION_NUEVA", mensaje="Ana se postuló.",
            leida=False, fecha=datetime.now(), postulacion_id=2, oferta_id=3,
        )
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: user(9)
        with patch(
            "src.routers.notificacion_router.NotificacionService.get_for_user",
            return_value=[notification],
        ) as get_for_user, patch(
            "src.routers.notificacion_router.NotificacionService.count_unread",
            return_value=1,
        ) as count_unread:
            client = TestClient(app)
            listed = client.get("/api/notificaciones")
            counted = client.get("/api/notificaciones/no-leidas/count")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["mensaje"], "Ana se postuló.")
        self.assertEqual(counted.json(), {"cantidad": 1})
        get_for_user.assert_called_once_with(9, 30, 0)
        count_unread.assert_called_once_with(9)

    def test_user_cannot_mark_another_users_notification_as_read(self):
        service = NotificacionService(Mock())
        service.repository = Mock()
        service.repository.get_by_id.return_value = SimpleNamespace(usuario_id=4)

        with self.assertRaises(ForbiddenError):
            service.mark_as_read(1, 9)
        service.repository.mark_as_read.assert_not_called()

    def test_postulation_response_includes_real_offer_title(self):
        model = SimpleNamespace(
            id=4, oferta_id=7, usuario_id=9, fecha=datetime.now(), estado="nueva",
            oferta=SimpleNamespace(titulo="Desarrollador Backend"),
        )
        result = PostulacionMapper.to_response_dto(model)

        self.assertEqual(result.oferta_id, 7)
        self.assertEqual(result.oferta_titulo, "Desarrollador Backend")
        self.assertEqual(result.estado, "nueva")

    def test_new_postulation_notifies_all_company_managers_only(self):
        service = PostulacionService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = user(9, "Ana")
        service.oferta_repository = Mock()
        service.oferta_repository.get_by_id.return_value = SimpleNamespace(id=7, empresa_id=3, titulo="Backend", publicada=True)
        service.repository = Mock()
        service.repository.get_by_oferta_and_usuario.return_value = None
        service.repository.create.return_value = SimpleNamespace(id=5, oferta_id=7, usuario_id=9, fecha=datetime.now(), estado="nueva", oferta=SimpleNamespace(titulo="Backend"))
        service.empresa_usuario_repository = Mock()
        service.empresa_usuario_repository.get_user_ids_by_empresa_and_roles.return_value = [1, 2]
        service.notificacion_service = Mock()

        service.create(CreatePostulacionDTO(oferta_id=7, usuario_id=9))

        created = service.notificacion_service.create_many.call_args.args[0]
        self.assertEqual([notification.usuario_id for notification in created], [1, 2])
        self.assertTrue(all(notification.tipo == "POSTULACION_NUEVA" for notification in created))
        self.assertTrue(all("Ana" in notification.mensaje and "Backend" in notification.mensaje for notification in created))

    def test_status_change_notifies_applicant_and_same_state_does_not(self):
        service = PostulacionService(Mock())
        existing = SimpleNamespace(id=5, oferta_id=7, usuario_id=9, estado="nueva")
        service.repository = Mock()
        service.repository.get_by_id.return_value = existing
        service.repository.get_by_id_for_update.return_value = existing
        service.repository.update.return_value = SimpleNamespace(id=5, oferta_id=7, usuario_id=9, fecha=datetime.now(), estado="vista", oferta=SimpleNamespace(titulo="Backend"))
        service.oferta_repository = Mock()
        service.oferta_repository.get_by_id.return_value = SimpleNamespace(id=7, empresa_id=3, titulo="Backend")
        service.empresa_usuario_repository = Mock()
        service.notificacion_service = Mock()

        service.update(5, UpdatePostulacionDTO(estado="vista"), 1)
        created = service.notificacion_service.create_many.call_args.args[0]
        self.assertEqual(created[0].usuario_id, 9)
        self.assertIn("VISTA", created[0].mensaje)

        service.repository.get_by_id_for_update.return_value = SimpleNamespace(
            id=5,
            oferta_id=7,
            usuario_id=9,
            estado="vista",
        )
        with self.assertRaises(ConflictError):
            service.update(5, UpdatePostulacionDTO(estado="vista"), 1)


if __name__ == "__main__":
    unittest.main()
