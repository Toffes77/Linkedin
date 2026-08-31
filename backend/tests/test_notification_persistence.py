import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.conexiones_model import Conexion
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.notificacion_model import Notificacion
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.seguimiento_model import Seguimiento
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
        self.company = Empresa(nombre=f"Empresa notificaciones {suffix}")
        self.db.add_all(
            [
                self.applicant,
                self.owner,
                self.recruiter,
                self.outsider,
                self.company,
            ]
        )
        self.db.flush()

        self.db.add_all(
            [
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.owner.id,
                    rol=RolEmpresa.OWNER,
                ),
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.recruiter.id,
                    rol=RolEmpresa.RECRUITER,
                ),
            ]
        )
        self.offer = Oferta(
            empresa_id=self.company.id,
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

    def test_hiring_unpublishes_offer_without_losing_application_history(self):
        second_applicant = self._user(
            f"second-applicant-{uuid4().hex}@example.com",
            "Segundo postulante",
        )
        self.db.add(second_applicant)
        self.db.commit()

        first_created = self.client.post(
            "/api/postulaciones",
            json={
                "oferta_id": self.offer.id,
                "usuario_id": self.applicant.id,
            },
        )
        self.assertEqual(first_created.status_code, 201, first_created.text)
        first_application_id = first_created.json()["id"]

        self.current_user = second_applicant
        second_created = self.client.post(
            "/api/postulaciones",
            json={
                "oferta_id": self.offer.id,
                "usuario_id": second_applicant.id,
            },
        )
        self.assertEqual(second_created.status_code, 201, second_created.text)
        second_application_id = second_created.json()["id"]

        self.current_user = self.owner
        for estado in ("vista", "entrevista", "contratado"):
            changed = self.client.patch(
                f"/api/postulaciones/{first_application_id}",
                json={"estado": estado},
            )
            self.assertEqual(changed.status_code, 200, changed.text)

        self.db.expire_all()
        stored_offer = self.db.get(Oferta, self.offer.id)
        self.assertIsNotNone(stored_offer)
        self.assertFalse(stored_offer.publicada)
        self.assertEqual(
            self.db.get(Postulacion, first_application_id).estado,
            "contratado",
        )
        self.assertEqual(
            self.db.get(Postulacion, second_application_id).estado,
            "nueva",
        )
        self.assertIsNotNone(
            self.db.get(
                EmpresaUsuario,
                (self.company.id, self.applicant.id),
            )
        )
        self.assertEqual(
            self.db.get(
                EmpresaUsuario,
                (self.company.id, self.applicant.id),
            ).rol,
            RolEmpresa.COLLABORATOR,
        )

        public_offers = self.client.get("/api/ofertas/publicadas")
        searched_offers = self.client.get(
            "/api/ofertas/publicadas",
            params={"q": "integración notificaciones"},
        )
        self.assertEqual(public_offers.status_code, 200, public_offers.text)
        self.assertEqual(searched_offers.status_code, 200, searched_offers.text)
        self.assertNotIn(
            self.offer.id,
            [offer["id"] for offer in public_offers.json()],
        )
        self.assertNotIn(
            self.offer.id,
            [offer["id"] for offer in searched_offers.json()],
        )

        self.current_user = self.applicant
        my_applications = self.client.get(
            f"/api/usuarios/{self.applicant.id}/postulaciones"
        )
        company_offers = self.client.get(
            f"/api/empresas/{self.company.id}/ofertas"
        )
        self.assertEqual(my_applications.status_code, 200, my_applications.text)
        self.assertEqual(company_offers.status_code, 200, company_offers.text)
        self.assertIn(
            first_application_id,
            [application["id"] for application in my_applications.json()],
        )
        self.assertEqual(
            next(
                application
                for application in my_applications.json()
                if application["id"] == first_application_id
            )["estado"],
            "contratado",
        )
        self.assertNotIn(
            self.offer.id,
            [offer["id"] for offer in company_offers.json()],
        )

        self.current_user = self.outsider
        rejected_application = self.client.post(
            "/api/postulaciones",
            json={
                "oferta_id": self.offer.id,
                "usuario_id": self.outsider.id,
            },
        )
        self.assertEqual(rejected_application.status_code, 409)
        self.assertEqual(
            self.db.query(Postulacion)
            .filter(Postulacion.oferta_id == self.offer.id)
            .count(),
            2,
        )

    def test_hiring_failure_rolls_back_status_membership_and_unpublishing(self):
        created = self.client.post(
            "/api/postulaciones",
            json={
                "oferta_id": self.offer.id,
                "usuario_id": self.applicant.id,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        application_id = created.json()["id"]

        self.current_user = self.owner
        for estado in ("vista", "entrevista"):
            changed = self.client.patch(
                f"/api/postulaciones/{application_id}",
                json={"estado": estado},
            )
            self.assertEqual(changed.status_code, 200, changed.text)

        with patch(
            "src.services.postulacion_service.NotificacionService.create_many",
            side_effect=RuntimeError("forced hiring notification failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "forced hiring notification failure",
            ):
                self.client.patch(
                    f"/api/postulaciones/{application_id}",
                    json={"estado": "contratado"},
                )

        self.db.expire_all()
        self.assertEqual(
            self.db.get(Postulacion, application_id).estado,
            "entrevista",
        )
        self.assertTrue(self.db.get(Oferta, self.offer.id).publicada)
        self.assertIsNone(
            self.db.get(
                EmpresaUsuario,
                (self.company.id, self.applicant.id),
            )
        )

    def test_follow_event_persists_once_and_supports_read_unfollow_and_refollow(self):
        self.current_user = self.applicant

        followed = self.client.post(f"/api/usuarios/{self.outsider.id}/seguir")
        self.assertEqual(followed.status_code, 200, followed.text)

        notifications = (
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == self.outsider.id,
                Notificacion.tipo == "NUEVO_SEGUIDOR",
            )
            .all()
        )
        self.assertEqual(len(notifications), 1)
        notification = notifications[0]
        self.assertEqual(notification.usuario_origen_id, self.applicant.id)
        self.assertEqual(
            notification.mensaje,
            f"{self.applicant.nombre} empezó a seguirte.",
        )
        self.assertFalse(notification.leida)

        self.current_user = self.outsider
        listed = self.client.get("/api/notificaciones")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()[0]["id"], notification.id)
        self.assertEqual(
            listed.json()[0]["usuario_origen_id"],
            self.applicant.id,
        )
        self.assertEqual(
            self.client.get("/api/notificaciones/no-leidas/count").json(),
            {"cantidad": 1},
        )

        marked = self.client.patch(f"/api/notificaciones/{notification.id}/leida")
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertTrue(marked.json()["leida"])
        self.assertEqual(
            self.client.get("/api/notificaciones/no-leidas/count").json(),
            {"cantidad": 0},
        )

        self.current_user = self.applicant
        duplicated = self.client.post(f"/api/usuarios/{self.outsider.id}/seguir")
        self.assertEqual(duplicated.status_code, 200, duplicated.text)
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == self.outsider.id,
                Notificacion.tipo == "NUEVO_SEGUIDOR",
            )
            .count(),
            1,
        )

        unfollowed = self.client.delete(f"/api/usuarios/{self.outsider.id}/seguir")
        self.assertEqual(unfollowed.status_code, 204, unfollowed.text)
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == self.outsider.id,
                Notificacion.tipo == "NUEVO_SEGUIDOR",
            )
            .count(),
            1,
        )

        followed_again = self.client.post(f"/api/usuarios/{self.outsider.id}/seguir")
        self.assertEqual(followed_again.status_code, 200, followed_again.text)
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == self.outsider.id,
                Notificacion.tipo == "NUEVO_SEGUIDOR",
            )
            .count(),
            2,
        )

        count_before_unfollow = self.db.query(Notificacion).count()
        self.client.delete(f"/api/usuarios/{self.outsider.id}/seguir")
        self.assertEqual(self.db.query(Notificacion).count(), count_before_unfollow)

        cannot_follow_self = self.client.post(
            f"/api/usuarios/{self.applicant.id}/seguir"
        )
        self.assertEqual(cannot_follow_self.status_code, 409, cannot_follow_self.text)

    def test_notification_failure_rolls_back_the_follow(self):
        self.current_user = self.applicant
        with patch(
            "src.services.seguimiento_service.NotificacionService.create_many",
            side_effect=RuntimeError("forced notification failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "forced notification failure"):
                self.client.post(f"/api/usuarios/{self.outsider.id}/seguir")

        self.assertIsNone(
            self.db.get(Seguimiento, (self.applicant.id, self.outsider.id))
        )

    def test_real_connection_flow_is_directional_notified_and_accepted_in_place(self):
        usuario_a = self.applicant
        usuario_b = self.outsider
        self.current_user = usuario_a

        initial = self.client.get(f"/api/conexiones/estado/{usuario_b.id}")
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()["estado"], "SIN_CONEXION")

        created = self.client.post(
            "/api/conexiones",
            json={"usuario_a": usuario_a.id, "usuario_b": usuario_b.id},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["estado"], "pendiente")

        connection_key = (
            min(usuario_a.id, usuario_b.id),
            max(usuario_a.id, usuario_b.id),
        )
        stored_connection = self.db.get(Conexion, connection_key)
        self.assertIsNotNone(stored_connection)
        self.assertEqual(stored_connection.estado, "pendiente")

        notification = (
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_b.id,
                Notificacion.tipo == "NUEVA_INVITACION_CONEXION",
            )
            .one()
        )
        self.assertEqual(notification.usuario_origen_id, usuario_a.id)
        self.assertEqual(
            notification.mensaje,
            f"{usuario_a.nombre} quiere conectar con vos.",
        )
        self.assertFalse(notification.leida)

        duplicate = self.client.post(
            "/api/conexiones",
            json={"usuario_a": usuario_a.id, "usuario_b": usuario_b.id},
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(
            self.db.query(Conexion)
            .filter(
                or_(
                    (Conexion.usuario_a == usuario_a.id)
                    & (Conexion.usuario_b == usuario_b.id),
                    (Conexion.usuario_a == usuario_b.id)
                    & (Conexion.usuario_b == usuario_a.id),
                )
            )
            .count(),
            1,
        )
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_b.id,
                Notificacion.tipo == "NUEVA_INVITACION_CONEXION",
            )
            .count(),
            1,
        )

        sent_status = self.client.get(f"/api/conexiones/estado/{usuario_b.id}")
        self.assertEqual(sent_status.json()["estado"], "PENDIENTE_ENVIADA")

        self.current_user = usuario_b
        received_status = self.client.get(f"/api/conexiones/estado/{usuario_a.id}")
        self.assertEqual(received_status.json()["estado"], "PENDIENTE_RECIBIDA")
        self.assertEqual(received_status.json()["usuario_a"], connection_key[0])
        self.assertEqual(received_status.json()["usuario_b"], connection_key[1])

        invitations = self.client.get("/api/conexiones/invitaciones-recibidas")
        self.assertEqual(invitations.status_code, 200, invitations.text)
        self.assertIn(
            usuario_a.id,
            [invitation["usuario"]["id"] for invitation in invitations.json()],
        )

        listed_notifications = self.client.get("/api/notificaciones")
        self.assertEqual(listed_notifications.status_code, 200, listed_notifications.text)
        listed_invitation = next(
            item
            for item in listed_notifications.json()
            if item["tipo"] == "NUEVA_INVITACION_CONEXION"
        )
        self.assertEqual(listed_invitation["usuario_origen_id"], usuario_a.id)

        followed = self.client.post(f"/api/usuarios/{usuario_a.id}/seguir")
        self.assertEqual(followed.status_code, 200, followed.text)
        self.assertIsNotNone(self.db.get(Seguimiento, (usuario_b.id, usuario_a.id)))
        self.assertEqual(
            self.client.get(f"/api/conexiones/estado/{usuario_a.id}").json()["estado"],
            "PENDIENTE_RECIBIDA",
        )

        self.current_user = usuario_a
        unread_before_acceptance = self.client.get(
            "/api/notificaciones/no-leidas/count"
        ).json()["cantidad"]
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_a.id,
                Notificacion.tipo == "CONEXION_ACEPTADA",
            )
            .count(),
            0,
        )

        self.current_user = usuario_b
        accepted = self.client.patch(
            f"/api/conexiones/{usuario_a.id}/{usuario_b.id}",
            json={"estado": "aceptada"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["estado"], "aceptada")
        self.assertIs(self.db.get(Conexion, connection_key), stored_connection)
        self.assertEqual(stored_connection.estado, "aceptada")

        acceptance_notification = (
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_a.id,
                Notificacion.tipo == "CONEXION_ACEPTADA",
            )
            .one()
        )
        self.assertEqual(acceptance_notification.usuario_origen_id, usuario_b.id)
        self.assertEqual(
            acceptance_notification.mensaje,
            f"{usuario_b.nombre} aceptó tu solicitud de conexión.",
        )
        self.assertFalse(acceptance_notification.leida)

        repeated_acceptance = self.client.patch(
            f"/api/conexiones/{usuario_a.id}/{usuario_b.id}",
            json={"estado": "aceptada"},
        )
        self.assertEqual(repeated_acceptance.status_code, 409, repeated_acceptance.text)
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_a.id,
                Notificacion.tipo == "CONEXION_ACEPTADA",
            )
            .count(),
            1,
        )

        self.assertEqual(
            self.client.get(f"/api/conexiones/estado/{usuario_a.id}").json()["estado"],
            "CONECTADO",
        )
        self.current_user = usuario_a
        listed_after_acceptance = self.client.get("/api/notificaciones")
        self.assertEqual(
            listed_after_acceptance.status_code,
            200,
            listed_after_acceptance.text,
        )
        listed_acceptance = next(
            item
            for item in listed_after_acceptance.json()
            if item["tipo"] == "CONEXION_ACEPTADA"
        )
        self.assertEqual(listed_acceptance["usuario_origen_id"], usuario_b.id)
        self.assertEqual(
            self.client.get("/api/notificaciones/no-leidas/count").json()["cantidad"],
            unread_before_acceptance + 1,
        )

        marked_acceptance = self.client.patch(
            f"/api/notificaciones/{acceptance_notification.id}/leida"
        )
        self.assertEqual(marked_acceptance.status_code, 200, marked_acceptance.text)
        self.assertTrue(marked_acceptance.json()["leida"])
        self.assertTrue(self.db.get(Notificacion, acceptance_notification.id).leida)
        self.assertEqual(
            self.client.get("/api/notificaciones/no-leidas/count").json()["cantidad"],
            unread_before_acceptance,
        )
        self.assertEqual(
            self.client.get(f"/api/conexiones/estado/{usuario_b.id}").json()["estado"],
            "CONECTADO",
        )

    def test_notification_failure_rolls_back_the_connection(self):
        self.current_user = self.applicant
        with patch(
            "src.services.conexion_service.NotificacionService.create_many",
            side_effect=RuntimeError("forced notification failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "forced notification failure"):
                self.client.post(
                    "/api/conexiones",
                    json={
                        "usuario_a": self.applicant.id,
                        "usuario_b": self.owner.id,
                    },
                )

        self.assertIsNone(
            self.db.get(
                Conexion,
                (
                    min(self.applicant.id, self.owner.id),
                    max(self.applicant.id, self.owner.id),
                ),
            )
        )
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == self.owner.id,
                Notificacion.tipo == "NUEVA_INVITACION_CONEXION",
            )
            .count(),
            0,
        )

    def test_notification_failure_rolls_back_connection_acceptance(self):
        self.current_user = self.applicant
        created = self.client.post(
            "/api/conexiones",
            json={
                "usuario_a": self.applicant.id,
                "usuario_b": self.owner.id,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)

        self.current_user = self.owner
        with patch(
            "src.services.conexion_service.NotificacionService.create_many",
            side_effect=RuntimeError("forced acceptance notification failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "forced acceptance notification failure",
            ):
                self.client.patch(
                    f"/api/conexiones/{self.applicant.id}/{self.owner.id}",
                    json={"estado": "aceptada"},
                )

        stored_connection = self.db.get(
            Conexion,
            (
                min(self.applicant.id, self.owner.id),
                max(self.applicant.id, self.owner.id),
            ),
        )
        self.assertIsNotNone(stored_connection)
        self.assertEqual(stored_connection.estado, "pendiente")
        self.assertEqual(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == self.applicant.id,
                Notificacion.tipo == "CONEXION_ACEPTADA",
            )
            .count(),
            0,
        )


if __name__ == "__main__":
    unittest.main()
