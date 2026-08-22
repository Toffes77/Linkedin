import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.notificacion_model import Notificacion
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La prueba de persistencia requiere la PostgreSQL configurada.",
)
class NotificationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

        suffix = uuid4().hex
        self.applicant = self._user(f"applicant-{suffix}@example.com", "Postulante")
        self.owner = self._user(f"owner-{suffix}@example.com", "Owner")
        self.recruiter = self._user(f"recruiter-{suffix}@example.com", "Recruiter")
        self.outsider = self._user(f"outsider-{suffix}@example.com", "Sin rol")
        company = Empresa(nombre=f"Empresa notificaciones {suffix}")
        self.db.add_all(
            [self.applicant, self.owner, self.recruiter, self.outsider, company]
        )
        self.db.flush()

        self.db.add_all(
            [
                EmpresaUsuario(
                    empresa_id=company.id,
                    usuario_id=self.owner.id,
                    rol=RolEmpresa.OWNER,
                ),
                EmpresaUsuario(
                    empresa_id=company.id,
                    usuario_id=self.recruiter.id,
                    rol=RolEmpresa.RECRUITER,
                ),
            ]
        )
        self.offer = Oferta(
            empresa_id=company.id,
            titulo="Oferta integración notificaciones",
            descripcion="Prueba de persistencia end-to-end.",
            publicada=True,
        )
        self.db.add(self.offer)
        self.db.flush()
        self.db.commit()

        self.current_user = self.applicant
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def _user(email: str, nombre: str) -> Usuario:
        return Usuario(
            email=email,
            nombre=nombre,
            password_hash="not-used-by-auth-override",
            headline="Prueba de integración",
            ciudad="Buenos Aires",
        )

    def test_real_events_persist_and_notification_api_reads_and_updates_them(self):
        created = self.client.post(
            "/api/postulaciones",
            json={"oferta_id": self.offer.id, "usuario_id": self.applicant.id},
        )
        self.assertEqual(created.status_code, 201, created.text)
        application_id = created.json()["id"]

        new_application_notifications = (
            self.db.query(Notificacion)
            .filter(
                Notificacion.postulacion_id == application_id,
                Notificacion.tipo == "POSTULACION_NUEVA",
            )
            .order_by(Notificacion.usuario_id)
            .all()
        )
        self.assertEqual(
            [notification.usuario_id for notification in new_application_notifications],
            sorted([self.owner.id, self.recruiter.id]),
        )
        self.assertNotIn(
            self.outsider.id,
            [notification.usuario_id for notification in new_application_notifications],
        )

        self.current_user = self.owner
        changed = self.client.patch(
            f"/api/postulaciones/{application_id}",
            json={"estado": "vista"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["estado"], "vista")

        state_notifications = (
            self.db.query(Notificacion)
            .filter(
                Notificacion.postulacion_id == application_id,
                Notificacion.tipo == "POSTULACION_ESTADO",
            )
            .all()
        )
        self.assertEqual(len(state_notifications), 1)
        self.assertEqual(state_notifications[0].usuario_id, self.applicant.id)
        self.assertIn(self.offer.titulo, state_notifications[0].mensaje)
        self.assertIn("VISTA", state_notifications[0].mensaje)

        count_before_same_state = self.db.query(Notificacion).count()
        same_state = self.client.patch(
            f"/api/postulaciones/{application_id}",
            json={"estado": "vista"},
        )
        self.assertEqual(same_state.status_code, 409, same_state.text)
        self.assertEqual(self.db.query(Notificacion).count(), count_before_same_state)

        listed = self.client.get("/api/notificaciones")
        unread = self.client.get("/api/notificaciones/no-leidas/count")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(unread.json(), {"cantidad": 1})
        owner_notification = listed.json()[0]
        self.assertEqual(owner_notification["usuario_id"], self.owner.id)

        marked = self.client.patch(
            f"/api/notificaciones/{owner_notification['id']}/leida"
        )
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertTrue(marked.json()["leida"])
        self.assertEqual(
            self.client.get("/api/notificaciones/no-leidas/count").json(),
            {"cantidad": 0},
        )
        self.assertTrue(
            self.db.get(Notificacion, owner_notification["id"]).leida
        )

    def test_notification_failure_rolls_back_the_application(self):
        with patch(
            "src.services.postulacion_service.NotificacionService.create_many",
            side_effect=RuntimeError("forced notification failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "forced notification failure"):
                self.client.post(
                    "/api/postulaciones",
                    json={
                        "oferta_id": self.offer.id,
                        "usuario_id": self.applicant.id,
                    },
                )

        self.assertIsNone(
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == self.offer.id,
                Postulacion.usuario_id == self.applicant.id,
            )
            .first()
        )


if __name__ == "__main__":
    unittest.main()
