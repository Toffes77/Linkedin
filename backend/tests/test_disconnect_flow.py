import threading
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import SessionLocal, engine, get_db
from src.db.models.conexiones_model import Conexion
from src.db.models.conversacion_model import Conversacion, Mensaje
from src.db.models.notificacion_model import Notificacion
from src.db.models.publicacion_model import Publicacion
from src.db.models.usuario_model import Usuario
from src.dtos.mensaje_dto import CrearConversacionDTO, EnviarMensajeDTO
from src.middlewares.auth_middleware import get_current_user
from src.repositories.conexion_repository import ConexionRepository
from src.services.conexion_service import ConexionService
from src.services.mensaje_service import MensajeService
from src.utils.errors import ForbiddenError, NotFoundError


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La integración de desconexión requiere PostgreSQL.",
)
class DisconnectFlowPostgresTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        with SessionLocal() as db:
            users = [
                Usuario(
                    email=f"disconnect-{name}-{suffix}@example.com",
                    nombre=name,
                    password_hash="hash",
                    headline="Perfil profesional",
                    ciudad="Argentina, Buenos Aires",
                )
                for name in ("Alicia", "Bruno", "Carla")
            ]
            db.add_all(users)
            db.flush()
            self.alicia_id, self.bruno_id, self.carla_id = (
                user.id for user in users
            )
            db.add(
                Conexion(
                    usuario_a=min(self.alicia_id, self.bruno_id),
                    usuario_b=max(self.alicia_id, self.bruno_id),
                    solicitante_id=self.alicia_id,
                    estado="aceptada",
                )
            )
            publication = Publicacion(
                autor_id=self.carla_id,
                texto="Publicación para comprobar el bloqueo al compartir.",
            )
            db.add(publication)
            db.commit()
            self.publication_id = publication.id

        self.db = SessionLocal()
        self.current_user = self.db.get(Usuario, self.alicia_id)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        with SessionLocal() as db:
            db.query(Notificacion).filter(
                or_(
                    Notificacion.usuario_id.in_(
                        (self.alicia_id, self.bruno_id, self.carla_id)
                    ),
                    Notificacion.usuario_origen_id.in_(
                        (self.alicia_id, self.bruno_id, self.carla_id)
                    ),
                )
            ).delete(synchronize_session=False)
            db.query(Conversacion).filter(
                Conversacion.usuario_menor_id
                == min(self.alicia_id, self.bruno_id),
                Conversacion.usuario_mayor_id
                == max(self.alicia_id, self.bruno_id),
            ).delete(synchronize_session=False)
            db.query(Conexion).filter(
                or_(
                    Conexion.usuario_a.in_(
                        (self.alicia_id, self.bruno_id, self.carla_id)
                    ),
                    Conexion.usuario_b.in_(
                        (self.alicia_id, self.bruno_id, self.carla_id)
                    ),
                )
            ).delete(synchronize_session=False)
            db.query(Publicacion).filter(
                Publicacion.id == self.publication_id
            ).delete(synchronize_session=False)
            db.query(Usuario).filter(
                Usuario.id.in_(
                    (self.alicia_id, self.bruno_id, self.carla_id)
                )
            ).delete(synchronize_session=False)
            db.commit()

    def _set_current_user(self, user_id: int) -> None:
        self.current_user = self.db.get(Usuario, user_id)

    def _create_conversation_with_history(self) -> tuple[int, list[int]]:
        service = MensajeService(self.db)
        conversation = service.get_or_create(
            CrearConversacionDTO(usuario_id=self.bruno_id),
            self.alicia_id,
        )
        first = service.send_message(
            conversation.id,
            EnviarMensajeDTO(contenido="Hola Bruno, ¿revisamos el proyecto?"),
            self.alicia_id,
        )
        second = service.send_message(
            conversation.id,
            EnviarMensajeDTO(contenido="Sí, mañana tengo disponibilidad."),
            self.bruno_id,
        )
        return conversation.id, [first.id, second.id]

    def test_complete_disconnect_history_and_reconnection_flow(self):
        conversation_id, historical_ids = self._create_conversation_with_history()

        response = self.client.delete(f"/api/conexiones/{self.bruno_id}")
        self.assertEqual(response.status_code, 204, response.text)
        self.assertIsNone(
            self.db.get(
                Conexion,
                (
                    min(self.alicia_id, self.bruno_id),
                    max(self.alicia_id, self.bruno_id),
                ),
            )
        )

        history = self.client.get(
            f"/api/conversaciones/{conversation_id}/mensajes"
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(
            [message["id"] for message in history.json()],
            historical_ids,
        )
        contacts = self.client.get("/api/conversaciones")
        self.assertEqual(contacts.status_code, 200, contacts.text)
        historical_contact = next(
            item
            for item in contacts.json()
            if item["usuario_id"] == self.bruno_id
        )
        self.assertFalse(historical_contact["conectados"])
        self.assertEqual(historical_contact["conversacion_id"], conversation_id)

        blocked_message = self.client.post(
            f"/api/conversaciones/{conversation_id}/mensajes",
            json={"contenido": "Este mensaje no debe persistirse."},
        )
        self.assertEqual(blocked_message.status_code, 403, blocked_message.text)
        self.assertEqual(
            blocked_message.json()["message"],
            "Ya no están conectados.",
        )
        blocked_share = self.client.post(
            f"/api/conversaciones/{conversation_id}/mensajes/publicaciones",
            json={"publicacion_id": self.publication_id},
        )
        self.assertEqual(blocked_share.status_code, 403, blocked_share.text)
        self.assertEqual(
            self.db.query(Mensaje)
            .filter(Mensaje.conversacion_id == conversation_id)
            .count(),
            2,
        )

        self._set_current_user(self.bruno_id)
        mark_read = self.client.post(
            f"/api/conversaciones/{conversation_id}/leer"
        )
        self.assertEqual(mark_read.status_code, 204, mark_read.text)
        self.assertTrue(self.db.get(Mensaje, historical_ids[0]).leido_por_destinatario)

        self._set_current_user(self.alicia_id)
        invitation = self.client.post(
            "/api/conexiones",
            json={"usuario_a": self.alicia_id, "usuario_b": self.bruno_id},
        )
        self.assertEqual(invitation.status_code, 201, invitation.text)
        self._set_current_user(self.bruno_id)
        accepted = self.client.patch(
            (
                f"/api/conexiones/{invitation.json()['usuario_a']}"
                f"/{invitation.json()['usuario_b']}"
            ),
            json={"estado": "aceptada"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)

        self._set_current_user(self.alicia_id)
        reopened = self.client.post(
            "/api/conversaciones",
            json={"usuario_id": self.bruno_id},
        )
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["id"], conversation_id)
        sent_again = self.client.post(
            f"/api/conversaciones/{conversation_id}/mensajes",
            json={"contenido": "Seguimos por este mismo chat."},
        )
        self.assertEqual(sent_again.status_code, 201, sent_again.text)
        self.assertEqual(
            self.db.query(Conversacion)
            .filter(
                Conversacion.usuario_menor_id
                == min(self.alicia_id, self.bruno_id),
                Conversacion.usuario_mayor_id
                == max(self.alicia_id, self.bruno_id),
            )
            .count(),
            1,
        )
        self.assertEqual(
            self.db.query(Mensaje)
            .filter(Mensaje.conversacion_id == conversation_id)
            .count(),
            3,
        )
        contacts_after_reconnect = self.client.get("/api/conversaciones").json()
        self.assertTrue(
            next(
                item
                for item in contacts_after_reconnect
                if item["usuario_id"] == self.bruno_id
            )["conectados"]
        )

    def test_outsider_cannot_delete_another_users_connection(self):
        self._set_current_user(self.carla_id)

        response = self.client.delete(f"/api/conexiones/{self.bruno_id}")

        self.assertEqual(response.status_code, 404, response.text)
        self.assertIsNotNone(
            self.db.get(
                Conexion,
                (
                    min(self.alicia_id, self.bruno_id),
                    max(self.alicia_id, self.bruno_id),
                ),
            )
        )

    def test_simultaneous_disconnects_have_one_success_and_one_controlled_error(self):
        barrier = threading.Barrier(2)
        outcomes: list[object] = []

        def disconnect(current_id: int, other_id: int) -> None:
            with SessionLocal() as db:
                barrier.wait(timeout=5)
                try:
                    ConexionService(db).delete(other_id, current_id)
                    outcomes.append("deleted")
                except Exception as error:
                    outcomes.append(error)

        first = threading.Thread(
            target=disconnect,
            args=(self.alicia_id, self.bruno_id),
        )
        second = threading.Thread(
            target=disconnect,
            args=(self.bruno_id, self.alicia_id),
        )
        first.start()
        second.start()
        first.join(timeout=5)
        second.join(timeout=5)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(outcomes.count("deleted"), 1)
        self.assertEqual(
            sum(isinstance(outcome, NotFoundError) for outcome in outcomes),
            1,
        )

    def test_disconnect_committed_while_message_waits_blocks_the_message(self):
        conversation_id, _ = self._create_conversation_with_history()
        before = self.db.query(Mensaje).filter(
            Mensaje.conversacion_id == conversation_id
        ).count()
        waiting_for_connection = threading.Event()
        outcome: dict[str, object] = {}

        def send_while_disconnects() -> None:
            with SessionLocal() as db:
                service = MensajeService(db)
                acquire = service.conexion_repository.get_by_id_for_update

                def announced_lock(usuario_a: int, usuario_b: int):
                    waiting_for_connection.set()
                    return acquire(usuario_a, usuario_b)

                service.conexion_repository.get_by_id_for_update = announced_lock
                try:
                    service.send_message(
                        conversation_id,
                        EnviarMensajeDTO(contenido="Mensaje concurrente"),
                        self.alicia_id,
                    )
                    outcome["sent"] = True
                except Exception as error:
                    outcome["error"] = error

        with SessionLocal() as disconnect_db:
            repository = ConexionRepository(disconnect_db)
            connection = repository.get_by_id_for_update(
                self.alicia_id,
                self.bruno_id,
            )
            self.assertIsNotNone(connection)
            repository.delete(connection, commit=False)

            worker = threading.Thread(target=send_while_disconnects)
            worker.start()
            self.assertTrue(waiting_for_connection.wait(timeout=5))
            self.assertTrue(worker.is_alive())
            disconnect_db.commit()

        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertIsInstance(outcome.get("error"), ForbiddenError)
        self.assertNotIn("sent", outcome)
        with Session(engine) as verification:
            self.assertEqual(
                verification.query(Mensaje)
                .filter(Mensaje.conversacion_id == conversation_id)
                .count(),
                before,
            )


if __name__ == "__main__":
    unittest.main()
