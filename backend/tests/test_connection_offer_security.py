import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import SessionLocal, engine, get_db
from src.db.models.conexiones_model import Conexion
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.notificacion_model import Notificacion
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.usuario_model import Usuario
from src.dtos.conexiones_dto import CreateConexionDTO, UpdateConexionDTO
from src.middlewares.auth_middleware import (
    get_current_user,
    get_optional_current_user,
)
from src.services.conexion_service import ConexionService
from src.utils.errors import ConflictError, ForbiddenError


def canonical_pair(first: int, second: int) -> tuple[int, int]:
    return min(first, second), max(first, second)


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Estas regresiones requieren la PostgreSQL configurada.",
)
class CanonicalConnectionSecurityTests(unittest.TestCase):
    def setUp(self):
        self.user_ids: list[int] = []
        suffix = uuid4().hex
        with SessionLocal() as db:
            users = [
                Usuario(
                    email=f"canonical-{index}-{suffix}@example.com",
                    nombre=f"Canonical {index}",
                    password_hash="not-used",
                    headline="Conexion segura",
                    ciudad="Buenos Aires",
                )
                for index in range(10)
            ]
            db.add_all(users)
            db.flush()
            self.user_ids = [user.id for user in users]
            db.commit()

    def tearDown(self):
        with SessionLocal() as db:
            db.query(Notificacion).filter(
                or_(
                    Notificacion.usuario_id.in_(self.user_ids),
                    Notificacion.usuario_origen_id.in_(self.user_ids),
                )
            ).delete(synchronize_session=False)
            db.query(Conexion).filter(
                or_(
                    Conexion.usuario_a.in_(self.user_ids),
                    Conexion.usuario_b.in_(self.user_ids),
                )
            ).delete(synchronize_session=False)
            db.query(Usuario).filter(Usuario.id.in_(self.user_ids)).delete(
                synchronize_session=False
            )
            db.commit()

    def _create(self, sender: int, recipient: int):
        with SessionLocal() as db:
            return ConexionService(db).create(
                CreateConexionDTO(usuario_a=sender, usuario_b=recipient),
                sender,
            )

    def _update(self, first: int, second: int, actor: int, state: str):
        with SessionLocal() as db:
            return ConexionService(db).update(
                first,
                second,
                UpdateConexionDTO(estado=state),
                actor,
            )

    def _stored(self, first: int, second: int) -> Conexion | None:
        with SessionLocal() as db:
            return db.get(Conexion, canonical_pair(first, second))

    def test_request_is_stored_once_in_canonical_orientation_and_pending(self):
        sender, recipient = self.user_ids[1], self.user_ids[0]

        created = self._create(sender, recipient)

        self.assertEqual((created.usuario_a, created.usuario_b), canonical_pair(sender, recipient))
        with SessionLocal() as db:
            stored = db.get(Conexion, canonical_pair(sender, recipient))
            self.assertIsNotNone(stored)
            self.assertEqual(stored.solicitante_id, sender)
            self.assertEqual(stored.estado, "pendiente")
            self.assertEqual(db.query(Conexion).filter(Conexion.usuario_a.in_((sender, recipient)), Conexion.usuario_b.in_((sender, recipient))).count(), 1)

    def test_inverse_request_is_rejected_without_second_row(self):
        first, second = self.user_ids[0], self.user_ids[1]
        self._create(first, second)

        with self.assertRaises(ConflictError):
            self._create(second, first)

        with SessionLocal() as db:
            self.assertEqual(db.query(Conexion).filter(Conexion.usuario_a == first, Conexion.usuario_b == second).count(), 1)

    def test_repeated_request_is_rejected_without_duplication(self):
        first, second = self.user_ids[0], self.user_ids[1]
        self._create(first, second)

        with self.assertRaises(ConflictError):
            self._create(first, second)

        self.assertIsNotNone(self._stored(first, second))

    def test_user_cannot_request_connection_to_self(self):
        with self.assertRaises(ConflictError):
            self._create(self.user_ids[0], self.user_ids[0])

    def test_database_rejects_noncanonical_and_self_pairs(self):
        low, high = self.user_ids[2], self.user_ids[3]
        with SessionLocal() as db:
            db.add(Conexion(usuario_a=high, usuario_b=low, solicitante_id=high))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

            db.add(Conexion(usuario_a=low, usuario_b=low, solicitante_id=low))
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_only_recipient_can_accept_and_contacts_are_symmetric(self):
        sender, recipient, outsider = self.user_ids[0:3]
        self._create(sender, recipient)

        with self.assertRaises(ForbiddenError):
            self._update(sender, recipient, sender, "aceptada")
        with self.assertRaises(ForbiddenError):
            self._update(recipient, sender, outsider, "aceptada")

        accepted = self._update(recipient, sender, recipient, "aceptada")
        self.assertEqual(accepted.estado, "aceptada")
        with SessionLocal() as db:
            repository = ConexionService(db).repository
            self.assertTrue(repository.has_accepted_connection(sender, recipient))
            self.assertTrue(repository.has_accepted_connection(recipient, sender))
            self.assertEqual(repository.count_accepted_by_user(sender), 1)
            self.assertEqual(repository.count_accepted_by_user(recipient), 1)

    def test_only_recipient_can_reject(self):
        sender, recipient, outsider = self.user_ids[3:6]
        self._create(sender, recipient)

        with self.assertRaises(ForbiddenError):
            self._update(sender, recipient, sender, "rechazada")
        with self.assertRaises(ForbiddenError):
            self._update(sender, recipient, outsider, "rechazada")

        rejected = self._update(sender, recipient, recipient, "rechazada")
        self.assertEqual(rejected.estado, "rechazada")

    def test_rejected_pair_remains_unique_and_cannot_be_recreated(self):
        sender, recipient = self.user_ids[0], self.user_ids[1]
        self._create(sender, recipient)
        self._update(sender, recipient, recipient, "rechazada")

        with self.assertRaises(ConflictError):
            self._create(recipient, sender)

        self.assertEqual(self._stored(sender, recipient).estado, "rechazada")

    def test_received_invitations_use_explicit_sender_after_canonicalization(self):
        sender, recipient = self.user_ids[5], self.user_ids[4]
        self.assertGreater(sender, recipient)
        self._create(sender, recipient)

        with SessionLocal() as db:
            invitations = ConexionService(db).get_invitaciones_recibidas(recipient)
            self.assertEqual(len(invitations), 1)
            self.assertEqual(invitations[0].usuario.id, sender)
            self.assertEqual(
                (invitations[0].usuario_a, invitations[0].usuario_b),
                canonical_pair(sender, recipient),
            )
            self.assertEqual(ConexionService(db).get_resumen_red(sender).invitaciones_enviadas, 1)

    def test_second_degree_suggestions_remain_symmetric_and_exclude_pending(self):
        viewer, direct, suggested, pending = self.user_ids[0:4]
        with SessionLocal() as db:
            db.add_all(
                [
                    Conexion(usuario_a=min(viewer, direct), usuario_b=max(viewer, direct), solicitante_id=viewer, estado="aceptada"),
                    Conexion(usuario_a=min(direct, suggested), usuario_b=max(direct, suggested), solicitante_id=direct, estado="aceptada"),
                    Conexion(usuario_a=min(direct, pending), usuario_b=max(direct, pending), solicitante_id=direct, estado="aceptada"),
                    Conexion(usuario_a=min(viewer, pending), usuario_b=max(viewer, pending), solicitante_id=viewer, estado="pendiente"),
                ]
            )
            db.commit()

        with SessionLocal() as db:
            ids = [user.id for user in ConexionService(db).get_second_degree_suggestions(viewer)]
            self.assertIn(suggested, ids)
            self.assertNotIn(viewer, ids)
            self.assertNotIn(direct, ids)
            self.assertNotIn(pending, ids)

    def test_concurrent_inverse_requests_finish_with_one_row_and_business_error(self):
        first, second = self.user_ids[6], self.user_ids[7]
        barrier = Barrier(2)

        def attempt(sender: int, recipient: int) -> tuple[str, int]:
            with SessionLocal() as db:
                pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
                service = ConexionService(db)
                original_lookup = service.repository.get_by_usuarios

                def synchronized_lookup(user_a: int, user_b: int):
                    result = original_lookup(user_a, user_b)
                    barrier.wait(timeout=5)
                    return result

                service.repository.get_by_usuarios = synchronized_lookup
                try:
                    service.create(
                        CreateConexionDTO(usuario_a=sender, usuario_b=recipient),
                        sender,
                    )
                    return "ok", pid
                except ConflictError:
                    return "conflict", pid

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda pair: attempt(*pair),
                    ((first, second), (second, first)),
                )
            )

        self.assertEqual(sorted(result for result, _ in results), ["conflict", "ok"])
        self.assertEqual(len({pid for _, pid in results}), 2)
        with SessionLocal() as db:
            self.assertEqual(db.query(Conexion).filter(Conexion.usuario_a == min(first, second), Conexion.usuario_b == max(first, second)).count(), 1)
            self.assertEqual(db.query(Notificacion).filter(Notificacion.usuario_id.in_((first, second)), Notificacion.tipo == "NUEVA_INVITACION_CONEXION").count(), 1)


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Estas regresiones requieren la PostgreSQL configurada.",
)
class PrivateOfferVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        suffix = uuid4().hex
        self.owner = self._user(f"offer-owner-{suffix}@example.com", "Owner")
        self.recruiter = self._user(f"offer-recruiter-{suffix}@example.com", "Recruiter")
        self.collaborator = self._user(f"offer-collaborator-{suffix}@example.com", "Collaborator")
        self.candidate = self._user(f"offer-candidate-{suffix}@example.com", "Candidate")
        self.other_candidate = self._user(f"offer-candidate-2-{suffix}@example.com", "Other candidate")
        self.other_owner = self._user(f"offer-other-owner-{suffix}@example.com", "Other owner")
        self.other_recruiter = self._user(f"offer-other-recruiter-{suffix}@example.com", "Other recruiter")
        self.company = Empresa(nombre=f"Offer company {suffix}")
        self.other_company = Empresa(nombre=f"Other offer company {suffix}")
        self.db.add_all([self.owner, self.recruiter, self.collaborator, self.candidate, self.other_candidate, self.other_owner, self.other_recruiter, self.company, self.other_company])
        self.db.flush()
        self.db.add_all(
            [
                EmpresaUsuario(empresa_id=self.company.id, usuario_id=self.owner.id, rol=RolEmpresa.OWNER),
                EmpresaUsuario(empresa_id=self.company.id, usuario_id=self.recruiter.id, rol=RolEmpresa.RECRUITER),
                EmpresaUsuario(empresa_id=self.company.id, usuario_id=self.collaborator.id, rol=RolEmpresa.COLLABORATOR),
                EmpresaUsuario(empresa_id=self.other_company.id, usuario_id=self.other_owner.id, rol=RolEmpresa.OWNER),
                EmpresaUsuario(empresa_id=self.other_company.id, usuario_id=self.other_recruiter.id, rol=RolEmpresa.RECRUITER),
            ]
        )
        self.public_offer = Oferta(empresa_id=self.company.id, titulo="Public security offer", descripcion="Public", publicada=True)
        self.draft_offer = Oferta(empresa_id=self.company.id, titulo="Secret Draft Match", descripcion="Private draft", publicada=False)
        self.hiring_offer = Oferta(empresa_id=self.company.id, titulo="Hiring security offer", descripcion="Will be unpublished", publicada=True)
        self.db.add_all([self.public_offer, self.draft_offer, self.hiring_offer])
        self.db.flush()
        self.historical_application = Postulacion(oferta_id=self.draft_offer.id, usuario_id=self.candidate.id, estado="nueva")
        self.hiring_application = Postulacion(oferta_id=self.hiring_offer.id, usuario_id=self.candidate.id, estado="entrevista")
        self.db.add_all([self.historical_application, self.hiring_application])
        self.db.commit()

        self.current_user = self.candidate
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        app.dependency_overrides[get_optional_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def _user(email: str, nombre: str) -> Usuario:
        return Usuario(email=email, nombre=nombre, password_hash="not-used", headline="Oferta segura", ciudad="Buenos Aires")

    def _as(self, user: Usuario) -> None:
        self.current_user = user

    def test_normal_and_unauthenticated_users_only_see_published_offer_by_id(self):
        published = self.client.get(f"/api/ofertas/{self.public_offer.id}")
        draft = self.client.get(f"/api/ofertas/{self.draft_offer.id}")
        self.assertEqual(published.status_code, 200, published.text)
        self.assertEqual(draft.status_code, 404, draft.text)

        app.dependency_overrides.pop(get_optional_current_user)
        try:
            anonymous_draft = self.client.get(f"/api/ofertas/{self.draft_offer.id}")
        finally:
            app.dependency_overrides[get_optional_current_user] = lambda: self.current_user
        self.assertEqual(anonymous_draft.status_code, 404, anonymous_draft.text)

    def test_correct_owner_and_recruiter_can_read_draft(self):
        for manager in (self.owner, self.recruiter):
            with self.subTest(role=manager.nombre):
                self._as(manager)
                response = self.client.get(f"/api/ofertas/{self.draft_offer.id}")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["titulo"], self.draft_offer.titulo)

    def test_collaborator_and_other_company_managers_cannot_read_draft(self):
        for unauthorized in (self.collaborator, self.other_owner, self.other_recruiter):
            with self.subTest(user=unauthorized.nombre):
                self._as(unauthorized)
                response = self.client.get(f"/api/ofertas/{self.draft_offer.id}")
                self.assertEqual(response.status_code, 404, response.text)
                self.assertNotIn("titulo", response.json())

    def test_public_list_and_search_never_include_drafts(self):
        self._as(self.candidate)
        listing = self.client.get("/api/ofertas/publicadas")
        search = self.client.get("/api/ofertas/publicadas", params={"q": "Secret Draft"})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertNotIn(self.draft_offer.id, [item["id"] for item in listing.json()])
        self.assertEqual(search.status_code, 200, search.text)
        self.assertEqual(search.json(), [])

    def test_company_listing_filters_drafts_except_for_correct_managers(self):
        for viewer in (self.candidate, self.collaborator, self.other_owner):
            with self.subTest(viewer=viewer.nombre):
                self._as(viewer)
                response = self.client.get(f"/api/empresas/{self.company.id}/ofertas")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn(self.draft_offer.id, [item["id"] for item in response.json()])

        for manager in (self.owner, self.recruiter):
            with self.subTest(manager=manager.nombre):
                self._as(manager)
                response = self.client.get(f"/api/empresas/{self.company.id}/ofertas")
                self.assertIn(self.draft_offer.id, [item["id"] for item in response.json()])

    def test_candidate_cannot_apply_to_draft(self):
        self._as(self.other_candidate)
        response = self.client.post(
            "/api/postulaciones",
            json={
                "oferta_id": self.draft_offer.id,
                "usuario_id": self.other_candidate.id,
            },
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db.query(Postulacion).filter(Postulacion.oferta_id == self.draft_offer.id, Postulacion.usuario_id == self.other_candidate.id).count(), 0)

    def test_my_applications_keeps_historical_unpublished_offer_context(self):
        self._as(self.candidate)
        response = self.client.get(f"/api/usuarios/{self.candidate.id}/postulaciones")
        self.assertEqual(response.status_code, 200, response.text)
        historical = next(item for item in response.json() if item["id"] == self.historical_application.id)
        self.assertEqual(historical["oferta_titulo"], self.draft_offer.titulo)

    def test_hiring_unpublishes_offer_without_losing_history_or_allowing_new_applications(self):
        self._as(self.owner)
        hired = self.client.patch(f"/api/postulaciones/{self.hiring_application.id}", json={"estado": "contratado"})
        self.assertEqual(hired.status_code, 200, hired.text)
        self.db.expire_all()
        self.assertFalse(self.db.get(Oferta, self.hiring_offer.id).publicada)

        self._as(self.other_candidate)
        self.assertEqual(self.client.get(f"/api/ofertas/{self.hiring_offer.id}").status_code, 404)
        public_ids = [item["id"] for item in self.client.get("/api/ofertas/publicadas").json()]
        self.assertNotIn(self.hiring_offer.id, public_ids)
        rejected = self.client.post(
            "/api/postulaciones",
            json={
                "oferta_id": self.hiring_offer.id,
                "usuario_id": self.other_candidate.id,
            },
        )
        self.assertEqual(rejected.status_code, 409, rejected.text)

        self._as(self.candidate)
        history = self.client.get(f"/api/usuarios/{self.candidate.id}/postulaciones")
        self.assertIn(self.hiring_application.id, [item["id"] for item in history.json()])

    def test_statistics_keep_owner_recruiter_only_policy(self):
        for manager in (self.owner, self.recruiter):
            with self.subTest(manager=manager.nombre):
                self._as(manager)
                self.assertEqual(self.client.get(f"/api/ofertas/{self.draft_offer.id}/estadisticas").status_code, 200)
        for unauthorized in (self.candidate, self.collaborator, self.other_owner):
            with self.subTest(user=unauthorized.nombre):
                self._as(unauthorized)
                self.assertEqual(self.client.get(f"/api/ofertas/{self.draft_offer.id}/estadisticas").status_code, 403)


if __name__ == "__main__":
    unittest.main()
