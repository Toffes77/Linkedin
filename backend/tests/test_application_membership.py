import threading
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.notificacion_model import Notificacion
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.usuario_model import Usuario
from src.dtos.postulacion_dto import CreatePostulacionDTO
from src.middlewares.auth_middleware import get_current_user
from src.repositories.empresa_usuario_repository import EmpresaUsuarioRepository
from src.services.postulacion_service import PostulacionService
from src.utils.datetime_utils import utc_now
from src.utils.errors import ConflictError


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La prueba de membresías requiere la PostgreSQL configurada.",
)
class ApplicationMembershipIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        suffix = uuid4().hex
        self.owner = self._user(f"owner-{suffix}@example.com", "Owner")
        self.recruiter = self._user(f"recruiter-{suffix}@example.com", "Recruiter")
        self.collaborator = self._user(
            f"collaborator-{suffix}@example.com",
            "Collaborator",
        )
        self.external = self._user(f"external-{suffix}@example.com", "External")
        self.other_company_member = self._user(
            f"other-member-{suffix}@example.com",
            "Other company member",
        )
        self.company = Empresa(nombre=f"Empresa postulaciones {suffix}")
        self.other_company = Empresa(nombre=f"Otra empresa {suffix}")
        self.db.add_all(
            [
                self.owner,
                self.recruiter,
                self.collaborator,
                self.external,
                self.other_company_member,
                self.company,
                self.other_company,
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
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.collaborator.id,
                    rol=RolEmpresa.COLLABORATOR,
                ),
                EmpresaUsuario(
                    empresa_id=self.other_company.id,
                    usuario_id=self.other_company_member.id,
                    rol=RolEmpresa.OWNER,
                ),
            ]
        )
        self.offer = self._offer("Oferta publicada", published=True)
        self.second_offer = self._offer("Segunda oferta publicada", published=True)
        self.draft = self._offer("Oferta no publicada", published=False)
        self.db.add_all([self.offer, self.second_offer, self.draft])
        self.db.flush()
        self.db.commit()

        self.current_user = self.external
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
    def _user(email: str, name: str) -> Usuario:
        return Usuario(
            email=email,
            nombre=name,
            password_hash="not-used-by-auth-override",
            headline="Perfil profesional",
            ciudad="Argentina, Buenos Aires",
        )

    def _offer(self, title: str, *, published: bool) -> Oferta:
        return Oferta(
            empresa=self.company,
            titulo=title,
            descripcion="Descripción válida para una oferta laboral.",
            publicada=published,
            fecha_publicacion=utc_now() if published else None,
        )

    def _apply_as(self, user: Usuario, offer: Oferta | None = None):
        self.current_user = user
        target = offer or self.offer
        return self.client.post(
            "/api/postulaciones",
            json={"oferta_id": target.id},
        )

    def _assert_member_is_blocked(self, user: Usuario) -> None:
        response = self._apply_as(user)

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["message"],
            "No podés postularte a una oferta de una empresa a la que pertenecés.",
        )
        self.assertEqual(
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == self.offer.id,
                Postulacion.usuario_id == user.id,
            )
            .count(),
            0,
        )
        self.assertEqual(self.db.execute(text("SELECT 1")).scalar_one(), 1)

    def test_owner_cannot_apply_to_own_company_offer(self):
        self._assert_member_is_blocked(self.owner)

    def test_recruiter_cannot_apply_to_own_company_offer(self):
        self._assert_member_is_blocked(self.recruiter)

    def test_collaborator_cannot_apply_to_own_company_offer(self):
        self._assert_member_is_blocked(self.collaborator)

    def test_external_user_can_apply_without_a_user_id_in_the_body(self):
        response = self._apply_as(self.external)

        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNotNone(
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == self.offer.id,
                Postulacion.usuario_id == self.external.id,
            )
            .first()
        )

    def test_application_cannot_be_created_for_another_user_by_manipulating_body(self):
        self.current_user = self.external
        response = self.client.post(
            "/api/postulaciones",
            json={"oferta_id": self.offer.id, "usuario_id": self.owner.id},
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertIsNone(
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == self.offer.id,
                Postulacion.usuario_id == self.owner.id,
            )
            .first()
        )

    def test_user_from_another_company_can_apply(self):
        response = self._apply_as(self.other_company_member)

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["usuario_id"], self.other_company_member.id)

    def test_missing_offer_keeps_not_found_behavior(self):
        self.current_user = self.external
        response = self.client.post(
            "/api/postulaciones",
            json={"oferta_id": 2_147_483_647},
        )

        self.assertEqual(response.status_code, 404, response.text)

    def test_unpublished_offer_keeps_conflict_behavior(self):
        response = self._apply_as(self.external, self.draft)

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            self.db.query(Postulacion)
            .filter(Postulacion.oferta_id == self.draft.id)
            .count(),
            0,
        )

    def test_duplicate_application_keeps_conflict_behavior(self):
        first = self._apply_as(self.external)
        duplicate = self._apply_as(self.external)

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(
            duplicate.json()["message"],
            "El usuario ya se postuló a esta oferta.",
        )
        self.assertEqual(
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == self.offer.id,
                Postulacion.usuario_id == self.external.id,
            )
            .count(),
            1,
        )

    def test_hiring_still_works_and_blocks_later_same_company_application(self):
        created = self._apply_as(self.external)
        self.assertEqual(created.status_code, 201, created.text)
        application_id = created.json()["id"]

        self.current_user = self.owner
        for state in ("vista", "entrevista", "contratado"):
            response = self.client.patch(
                f"/api/postulaciones/{application_id}",
                json={"estado": state},
            )
            self.assertEqual(response.status_code, 200, response.text)

        membership = self.db.get(
            EmpresaUsuario,
            (self.company.id, self.external.id),
        )
        self.assertIsNotNone(membership)
        self.assertEqual(membership.rol, RolEmpresa.COLLABORATOR)

        blocked = self._apply_as(self.external, self.second_offer)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(
            self.db.query(Postulacion)
            .filter(
                Postulacion.oferta_id == self.second_offer.id,
                Postulacion.usuario_id == self.external.id,
            )
            .count(),
            0,
        )


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La prueba concurrente requiere PostgreSQL.",
)
class ApplicationMembershipConcurrencyTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        with Session(engine) as db:
            self.applicant = ApplicationMembershipIntegrationTests._user(
                f"race-applicant-{suffix}@example.com",
                "Race applicant",
            )
            self.owner = ApplicationMembershipIntegrationTests._user(
                f"race-owner-{suffix}@example.com",
                "Race owner",
            )
            self.company = Empresa(nombre=f"Empresa carrera {suffix}")
            db.add_all([self.applicant, self.owner, self.company])
            db.flush()
            db.add(
                EmpresaUsuario(
                    empresa_id=self.company.id,
                    usuario_id=self.owner.id,
                    rol=RolEmpresa.OWNER,
                )
            )
            self.offer = Oferta(
                empresa_id=self.company.id,
                titulo="Oferta concurrente",
                descripcion="Oferta para comprobar la exclusión concurrente.",
                publicada=True,
                fecha_publicacion=utc_now(),
            )
            db.add(self.offer)
            db.commit()
            self.applicant_id = self.applicant.id
            self.owner_id = self.owner.id
            self.company_id = self.company.id
            self.offer_id = self.offer.id

    def tearDown(self):
        with Session(engine) as db:
            db.query(Notificacion).filter(
                Notificacion.oferta_id == self.offer_id
            ).delete(synchronize_session=False)
            db.query(Postulacion).filter(
                Postulacion.oferta_id == self.offer_id
            ).delete(synchronize_session=False)
            db.query(EmpresaUsuario).filter(
                EmpresaUsuario.empresa_id == self.company_id
            ).delete(synchronize_session=False)
            db.query(Oferta).filter(Oferta.id == self.offer_id).delete(
                synchronize_session=False
            )
            db.query(Empresa).filter(Empresa.id == self.company_id).delete(
                synchronize_session=False
            )
            db.query(Usuario).filter(
                Usuario.id.in_((self.applicant_id, self.owner_id))
            ).delete(synchronize_session=False)
            db.commit()

    def test_membership_committed_while_application_waits_blocks_application(self):
        waiting_for_lock = threading.Event()
        outcome: dict[str, object] = {}

        def apply_in_parallel():
            with Session(engine) as application_db:
                service = PostulacionService(application_db)
                acquire_lock = service.empresa_usuario_repository.lock_membership_scope

                def announced_lock(empresa_id: int, usuario_id: int):
                    waiting_for_lock.set()
                    return acquire_lock(empresa_id, usuario_id)

                service.empresa_usuario_repository.lock_membership_scope = announced_lock
                try:
                    service.create(
                        CreatePostulacionDTO(
                            oferta_id=self.offer_id,
                            usuario_id=self.applicant_id,
                        )
                    )
                    outcome["created"] = True
                except Exception as exc:  # La aserción valida el tipo exacto.
                    outcome["error"] = exc

        with Session(engine) as membership_db:
            repository = EmpresaUsuarioRepository(membership_db)
            repository.lock_membership_scope(self.company_id, self.applicant_id)
            membership_db.add(
                EmpresaUsuario(
                    empresa_id=self.company_id,
                    usuario_id=self.applicant_id,
                    rol=RolEmpresa.COLLABORATOR,
                )
            )
            membership_db.flush()

            worker = threading.Thread(target=apply_in_parallel)
            worker.start()
            self.assertTrue(waiting_for_lock.wait(timeout=5))
            self.assertTrue(worker.is_alive())
            membership_db.commit()

        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertIsInstance(outcome.get("error"), ConflictError)
        self.assertNotIn("created", outcome)

        with Session(engine) as verification_db:
            self.assertIsNotNone(
                verification_db.get(
                    EmpresaUsuario,
                    (self.company_id, self.applicant_id),
                )
            )
            self.assertEqual(
                verification_db.query(Postulacion)
                .filter(
                    Postulacion.oferta_id == self.offer_id,
                    Postulacion.usuario_id == self.applicant_id,
                )
                .count(),
                0,
            )


if __name__ == "__main__":
    unittest.main()
