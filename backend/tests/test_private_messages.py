import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.conexiones_model import Conexion
from src.db.models.conversacion_model import Conversacion, ConversacionUsuario, Mensaje
from src.db.models.notificacion_model import Notificacion
from src.db.models.usuario_model import Usuario
from src.dtos.mensaje_dto import CrearConversacionDTO, EnviarMensajeDTO, MensajeDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.mensaje_service import MensajeService
from src.utils.errors import BadRequestError, ForbiddenError


def usuario(usuario_id: int, nombre: str = "Usuario"):
    return SimpleNamespace(
        id=usuario_id,
        nombre=nombre,
        headline="Headline",
        foto_perfil_url=None,
    )


def conversacion(conversacion_id: int = 8, menor: int = 1, mayor: int = 2):
    return SimpleNamespace(
        id=conversacion_id,
        usuario_menor_id=menor,
        usuario_mayor_id=mayor,
        fecha_creacion=datetime(2026, 8, 24, 10, 0),
    )


class PrivateMessageServiceTests(unittest.TestCase):
    def service(self) -> MensajeService:
        service = MensajeService(Mock())
        service.repository = Mock()
        service.conexion_repository = Mock()
        service.usuario_repository = Mock()
        return service

    def test_creates_conversation_only_for_accepted_contact(self):
        service = self.service()
        service.usuario_repository.get_by_id.return_value = usuario(9)
        service.conexion_repository.has_accepted_connection.return_value = True
        service.repository.get_by_pair.return_value = None
        service.repository.create.return_value = conversacion(4, 3, 9)

        result = service.get_or_create(CrearConversacionDTO(usuario_id=9), 3)

        service.repository.create.assert_called_once_with(3, 9)
        self.assertEqual(result.id, 4)
        self.assertEqual(result.usuario_id, 9)

    def test_reuses_existing_conversation_in_reverse_direction(self):
        service = self.service()
        service.usuario_repository.get_by_id.return_value = usuario(3)
        service.conexion_repository.has_accepted_connection.return_value = True
        existing = conversacion(4, 3, 9)
        service.repository.get_by_pair.return_value = existing

        result = service.get_or_create(CrearConversacionDTO(usuario_id=3), 9)

        service.repository.create.assert_not_called()
        self.assertEqual(result.id, 4)
        self.assertEqual(result.usuario_id, 3)

    def test_rejects_users_that_are_not_accepted_contacts(self):
        service = self.service()
        service.usuario_repository.get_by_id.return_value = usuario(9)
        service.conexion_repository.has_accepted_connection.return_value = False

        with self.assertRaises(ForbiddenError):
            service.get_or_create(CrearConversacionDTO(usuario_id=9), 3)

    def test_rejects_conversation_with_self(self):
        service = self.service()
        with self.assertRaises(BadRequestError):
            service.get_or_create(CrearConversacionDTO(usuario_id=3), 3)

    def test_sender_is_always_authenticated_user_and_content_is_trimmed(self):
        service = self.service()
        current_conversation = conversacion()
        service.repository.get_by_id.return_value = current_conversation
        service.repository.get_participation.return_value = SimpleNamespace()
        sent = SimpleNamespace(
            id=17,
            conversacion_id=8,
            autor_id=1,
            contenido="Hola",
            fecha=datetime.now(),
        )
        service.repository.create_message.return_value = sent

        result = service.send_message(
            8,
            EnviarMensajeDTO(contenido="  Hola  "),
            usuario_id=1,
        )

        service.repository.create_message.assert_called_once_with(
            current_conversation,
            autor_id=1,
            contenido="Hola",
        )
        self.assertEqual(result.autor_id, 1)

    def test_rejects_empty_and_too_long_messages(self):
        service = self.service()
        service.repository.get_by_id.return_value = conversacion()
        service.repository.get_participation.return_value = SimpleNamespace()
        with self.assertRaises(BadRequestError):
            service.send_message(8, EnviarMensajeDTO(contenido="   "), 1)
        with self.assertRaises(ValueError):
            EnviarMensajeDTO(contenido="x" * 2001)

    def test_denies_messages_and_read_state_for_foreign_conversation(self):
        service = self.service()
        service.repository.get_by_id.return_value = conversacion()
        service.repository.get_participation.return_value = None

        with self.assertRaises(ForbiddenError):
            service.get_messages(8, usuario_id=30, limit=30, offset=0)
        with self.assertRaises(ForbiddenError):
            service.mark_as_read(8, usuario_id=30)

    def test_message_pagination_is_forwarded_to_repository(self):
        service = self.service()
        service.repository.get_by_id.return_value = conversacion()
        service.repository.get_participation.return_value = SimpleNamespace()
        service.repository.get_messages.return_value = []

        service.get_messages(8, usuario_id=1, limit=20, offset=40)

        service.repository.get_messages.assert_called_once_with(8, 20, 40)

    def test_contact_mapping_keeps_conversations_and_contacts_without_messages(self):
        service = self.service()
        active = conversacion()
        last = SimpleNamespace(
            contenido="Último",
            autor_id=2,
            fecha=datetime(2026, 8, 24, 12, 0),
        )
        service.repository.list_contact_summaries.return_value = [
            (usuario(2, "Ana"), active, last, 2),
            (usuario(3, "Bruno"), None, None, 0),
        ]

        result = service.list_contacts(1)

        self.assertEqual([item.nombre for item in result], ["Ana", "Bruno"])
        self.assertEqual(result[0].no_leidos, 2)
        self.assertIsNone(result[1].conversacion_id)


class PrivateMessageRouterTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: usuario(7)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_send_endpoint_never_accepts_author_id(self):
        created = MensajeDTO(
            id=4,
            conversacion_id=2,
            autor_id=7,
            contenido="Hola",
            fecha=datetime(2026, 8, 24, 10, 0),
        )
        with patch(
            "src.routers.mensaje_router.MensajeService.send_message",
            return_value=created,
        ) as send:
            response = TestClient(app).post(
                "/api/conversaciones/2/mensajes",
                json={"contenido": "Hola", "autor_id": 999},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(send.call_args.args[2], 7)

    def test_empty_message_is_rejected_by_schema(self):
        response = TestClient(app).post(
            "/api/conversaciones/2/mensajes",
            json={"contenido": "   "},
        )
        self.assertEqual(response.status_code, 422)

    def test_messages_endpoints_require_authentication(self):
        app.dependency_overrides.pop(get_current_user)
        response = TestClient(app).get("/api/conversaciones")
        self.assertEqual(response.status_code, 401)


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La prueba de persistencia requiere la PostgreSQL configurada.",
)
class PrivateMessagePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        suffix = uuid4().hex
        self.alicia = self._user(f"alicia-{suffix}@example.com", "Alicia")
        self.bruno = self._user(f"bruno-{suffix}@example.com", "Bruno")
        self.carla = self._user(f"carla-{suffix}@example.com", "Carla")
        self.outsider = self._user(f"out-{suffix}@example.com", "No Contacto")
        self.db.add_all(
            [
                Conexion(
                    usuario_a=self.alicia.id,
                    usuario_b=self.bruno.id,
                    estado="aceptada",
                ),
                Conexion(
                    usuario_a=self.carla.id,
                    usuario_b=self.alicia.id,
                    estado="aceptada",
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def _user(self, email: str, nombre: str) -> Usuario:
        model = Usuario(
            email=email,
            nombre=nombre,
            password_hash="hash",
            headline=f"{nombre} headline",
            ciudad="Buenos Aires",
        )
        self.db.add(model)
        self.db.flush()
        return model

    def test_real_database_reuses_pair_and_lists_contact_without_chat(self):
        service = MensajeService(self.db)
        first = service.get_or_create(
            CrearConversacionDTO(usuario_id=self.bruno.id),
            self.alicia.id,
        )
        second = service.get_or_create(
            CrearConversacionDTO(usuario_id=self.alicia.id),
            self.bruno.id,
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(
            self.db.query(Conversacion)
            .filter(Conversacion.id == first.id)
            .count(),
            1,
        )
        contacts = service.list_contacts(self.alicia.id)
        self.assertEqual({item.nombre for item in contacts}, {"Bruno", "Carla"})
        carla = next(item for item in contacts if item.nombre == "Carla")
        self.assertIsNone(carla.conversacion_id)

    def test_real_database_unread_read_order_and_no_notifications(self):
        service_a = MensajeService(self.db)
        conversation_b = service_a.get_or_create(
            CrearConversacionDTO(usuario_id=self.bruno.id), self.alicia.id
        )
        conversation_c = service_a.get_or_create(
            CrearConversacionDTO(usuario_id=self.carla.id), self.alicia.id
        )
        notifications_before = self.db.query(Notificacion).count()

        MensajeService(self.db).send_message(
            conversation_b.id,
            EnviarMensajeDTO(contenido="Mensaje de Bruno"),
            self.bruno.id,
        )
        MensajeService(self.db).send_message(
            conversation_c.id,
            EnviarMensajeDTO(contenido="Mensaje de Carla"),
            self.carla.id,
        )

        contacts = service_a.list_contacts(self.alicia.id)
        self.assertEqual([item.nombre for item in contacts], ["Carla", "Bruno"])
        self.assertEqual(service_a.count_unread(self.alicia.id), 2)
        self.assertEqual(service_a.count_unread(self.bruno.id), 0)
        self.assertEqual(self.db.query(Notificacion).count(), notifications_before)

        service_a.mark_as_read(conversation_c.id, self.alicia.id)
        self.assertEqual(service_a.count_unread(self.alicia.id), 1)
        carla = next(item for item in service_a.list_contacts(self.alicia.id) if item.nombre == "Carla")
        self.assertEqual(carla.no_leidos, 0)

    def test_real_database_pagination_and_two_way_exchange(self):
        service = MensajeService(self.db)
        conversation_dto = service.get_or_create(
            CrearConversacionDTO(usuario_id=self.bruno.id), self.alicia.id
        )
        for index in range(5):
            author = self.alicia.id if index % 2 == 0 else self.bruno.id
            service.send_message(
                conversation_dto.id,
                EnviarMensajeDTO(contenido=f"Mensaje {index}"),
                author,
            )

        page = service.get_messages(
            conversation_dto.id,
            self.alicia.id,
            limit=2,
            offset=0,
        )
        previous_page = service.get_messages(
            conversation_dto.id,
            self.alicia.id,
            limit=2,
            offset=2,
        )
        self.assertEqual([item.contenido for item in page], ["Mensaje 3", "Mensaje 4"])
        self.assertEqual(
            [item.contenido for item in previous_page],
            ["Mensaje 1", "Mensaje 2"],
        )

    def test_real_database_denies_outsider(self):
        service = MensajeService(self.db)
        conversation_dto = service.get_or_create(
            CrearConversacionDTO(usuario_id=self.bruno.id), self.alicia.id
        )
        with self.assertRaises(ForbiddenError):
            service.get_messages(
                conversation_dto.id,
                self.outsider.id,
                limit=30,
                offset=0,
            )
        with self.assertRaises(ForbiddenError):
            service.send_message(
                conversation_dto.id,
                EnviarMensajeDTO(contenido="Intrusión"),
                self.outsider.id,
            )


if __name__ == "__main__":
    unittest.main()
