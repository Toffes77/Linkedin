import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4

from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError

from src.app import app  # noqa: F401 - registra todos los modelos SQLAlchemy
from src.db.connection import SessionLocal, engine
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.notificacion_model import Notificacion
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.usuario_model import Usuario
from src.dtos.empresa_dto import CreateEmpresaDTO
from src.dtos.empresa_usuario_dto import (
    CreateEmpresaUsuarioDTO,
    UpdateEmpresaUsuarioDTO,
)
from src.dtos.postulacion_dto import UpdatePostulacionDTO
from src.repositories.empresa_repository import EmpresaRepository
from src.repositories.postulacion_repository import PostulacionRepository
from src.services.empresa_service import EmpresaService
from src.services.empresa_usuario_service import EmpresaUsuarioService
from src.services.postulacion_service import PostulacionService
from src.utils.errors import ConflictError, ForbiddenError


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Las pruebas concurrentes requieren la PostgreSQL configurada.",
)
class IntegrityConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.company_ids: list[int] = []
        self.offer_ids: list[int] = []
        self.application_ids: list[int] = []
        self.user_ids: list[int] = []

        suffix = uuid4().hex
        with SessionLocal() as db:
            self.owner_a = self._user(f"owner-a-{suffix}@example.com", "Owner A")
            self.owner_b = self._user(f"owner-b-{suffix}@example.com", "Owner B")
            self.recruiter = self._user(
                f"recruiter-{suffix}@example.com",
                "Recruiter",
            )
            self.collaborator = self._user(
                f"collaborator-{suffix}@example.com",
                "Collaborator",
            )
            self.applicant = self._user(
                f"applicant-{suffix}@example.com",
                "Applicant",
            )
            self.rejected_applicant = self._user(
                f"rejected-{suffix}@example.com",
                "Rejected applicant",
            )
            db.add_all(
                [
                    self.owner_a,
                    self.owner_b,
                    self.recruiter,
                    self.collaborator,
                    self.applicant,
                    self.rejected_applicant,
                ]
            )
            db.flush()
            self.user_ids.extend(
                [
                    self.owner_a.id,
                    self.owner_b.id,
                    self.recruiter.id,
                    self.collaborator.id,
                    self.applicant.id,
                    self.rejected_applicant.id,
                ]
            )

            self.company = Empresa(nombre=f"Empresa concurrencia {suffix}")
            db.add(self.company)
            db.flush()
            self.company_ids.append(self.company.id)
            db.add_all(
                [
                    EmpresaUsuario(
                        empresa_id=self.company.id,
                        usuario_id=self.owner_a.id,
                        rol=RolEmpresa.OWNER,
                    ),
                    EmpresaUsuario(
                        empresa_id=self.company.id,
                        usuario_id=self.owner_b.id,
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
                ]
            )

            self.offer = Oferta(
                empresa_id=self.company.id,
                titulo="Oferta concurrente",
                descripcion="Prueba de integridad concurrente.",
                publicada=True,
            )
            db.add(self.offer)
            db.flush()
            self.offer_ids.append(self.offer.id)
            self.application = Postulacion(
                oferta_id=self.offer.id,
                usuario_id=self.applicant.id,
                estado="entrevista",
            )
            self.rejected_application = Postulacion(
                oferta_id=self.offer.id,
                usuario_id=self.rejected_applicant.id,
                estado="rechazada",
            )
            db.add_all([self.application, self.rejected_application])
            db.flush()
            self.application_ids.extend(
                [self.application.id, self.rejected_application.id]
            )
            db.commit()

            self.company_id = self.company.id
            self.offer_id = self.offer.id
            self.application_id = self.application.id
            self.rejected_application_id = self.rejected_application.id
            self.owner_a_id = self.owner_a.id
            self.owner_b_id = self.owner_b.id
            self.recruiter_id = self.recruiter.id
            self.collaborator_id = self.collaborator.id
            self.applicant_id = self.applicant.id
            self.rejected_applicant_id = self.rejected_applicant.id

    def tearDown(self):
        with SessionLocal() as db:
            db.query(Notificacion).filter(
                or_(
                    Notificacion.usuario_id.in_(self.user_ids),
                    Notificacion.usuario_origen_id.in_(self.user_ids),
                    Notificacion.oferta_id.in_(self.offer_ids),
                    Notificacion.postulacion_id.in_(self.application_ids),
                )
            ).delete(synchronize_session=False)
            db.query(Postulacion).filter(
                Postulacion.id.in_(self.application_ids)
            ).delete(synchronize_session=False)
            db.query(EmpresaUsuario).filter(
                EmpresaUsuario.empresa_id.in_(self.company_ids)
            ).delete(synchronize_session=False)
            db.query(Oferta).filter(Oferta.id.in_(self.offer_ids)).delete(
                synchronize_session=False
            )
            db.query(Empresa).filter(Empresa.id.in_(self.company_ids)).delete(
                synchronize_session=False
            )
            db.query(Usuario).filter(Usuario.id.in_(self.user_ids)).delete(
                synchronize_session=False
            )
            db.commit()

    @staticmethod
    def _user(email: str, nombre: str) -> Usuario:
        return Usuario(
            email=email,
            nombre=nombre,
            password_hash="not-used-in-concurrency-tests",
            headline="Perfil de concurrencia",
            ciudad="Buenos Aires",
        )

    def _application_update(
        self,
        state: str,
        *,
        barrier: Barrier | None = None,
        attempted: Event | None = None,
        finished: Event | None = None,
    ) -> tuple[str, int]:
        with SessionLocal() as db:
            backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            service = PostulacionService(db)
            if attempted is not None:
                original = service.repository.get_by_id_for_update

                def marked_get(application_id: int):
                    attempted.set()
                    return original(application_id)

                service.repository.get_by_id_for_update = marked_get
            if barrier is not None:
                barrier.wait(timeout=5)
            try:
                service.update(
                    self.application_id,
                    UpdatePostulacionDTO(estado=state),
                    self.owner_a_id,
                )
                result = "ok"
            except ConflictError:
                result = "conflict"
            finally:
                if finished is not None:
                    finished.set()
            return result, backend_pid

    def _member_update(
        self,
        user_id: int,
        new_role: RolEmpresa,
        *,
        barrier: Barrier | None = None,
        attempted: Event | None = None,
        finished: Event | None = None,
    ) -> tuple[str, int]:
        with SessionLocal() as db:
            backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            service = EmpresaUsuarioService(db)
            if attempted is not None:
                original = service.empresa_repository.get_by_id_for_update

                def marked_get(company_id: int):
                    attempted.set()
                    return original(company_id)

                service.empresa_repository.get_by_id_for_update = marked_get
            if barrier is not None:
                barrier.wait(timeout=5)
            try:
                service.update(
                    self.company_id,
                    user_id,
                    UpdateEmpresaUsuarioDTO(rol=new_role),
                    user_id,
                )
                result = "ok"
            except (ConflictError, ForbiddenError):
                result = "rejected"
            finally:
                if finished is not None:
                    finished.set()
            return result, backend_pid

    def _member_delete(
        self,
        user_id: int,
        *,
        barrier: Barrier | None = None,
        attempted: Event | None = None,
        finished: Event | None = None,
    ) -> tuple[str, int]:
        with SessionLocal() as db:
            backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            service = EmpresaUsuarioService(db)
            if attempted is not None:
                original = service.empresa_repository.get_by_id_for_update

                def marked_get(company_id: int):
                    attempted.set()
                    return original(company_id)

                service.empresa_repository.get_by_id_for_update = marked_get
            if barrier is not None:
                barrier.wait(timeout=5)
            try:
                service.delete(self.company_id, user_id, user_id)
                result = "ok"
            except (ConflictError, ForbiddenError):
                result = "rejected"
            finally:
                if finished is not None:
                    finished.set()
            return result, backend_pid

    def test_waiting_application_transition_reloads_state_after_row_lock(self):
        attempted = Event()
        finished = Event()
        with SessionLocal() as first_db:
            first_pid = first_db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            locked = PostulacionRepository(first_db).get_by_id_for_update(
                self.application_id
            )
            self.assertEqual(locked.estado, "entrevista")

            with ThreadPoolExecutor(max_workers=1) as executor:
                waiting = executor.submit(
                    self._application_update,
                    "contratado",
                    attempted=attempted,
                    finished=finished,
                )
                self.assertTrue(attempted.wait(timeout=3))
                self.assertFalse(finished.wait(timeout=0.2))

                rejected = PostulacionService(first_db).update(
                    self.application_id,
                    UpdatePostulacionDTO(estado="rechazada"),
                    self.owner_a_id,
                )
                self.assertEqual(rejected.estado, "rechazada")
                waiting_result, waiting_pid = waiting.result(timeout=5)

        self.assertNotEqual(first_pid, waiting_pid)
        self.assertEqual(waiting_result, "conflict")
        with SessionLocal() as db:
            self.assertEqual(
                db.get(Postulacion, self.application_id).estado,
                "rechazada",
            )
            self.assertIsNone(
                db.get(EmpresaUsuario, (self.company_id, self.applicant_id))
            )
            self.assertTrue(db.get(Oferta, self.offer_id).publicada)

    def test_two_simultaneous_hires_create_one_logical_hiring(self):
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [
                executor.submit(
                    self._application_update,
                    "contratado",
                    barrier=barrier,
                )
                for _ in range(2)
            ]
            outcomes = [future.result(timeout=8) for future in results]

        self.assertEqual(sorted(result for result, _pid in outcomes), ["conflict", "ok"])
        self.assertEqual(len({pid for _result, pid in outcomes}), 2)
        with SessionLocal() as db:
            self.assertEqual(
                db.get(Postulacion, self.application_id).estado,
                "contratado",
            )
            self.assertFalse(db.get(Oferta, self.offer_id).publicada)
            self.assertEqual(
                db.query(EmpresaUsuario)
                .filter(
                    EmpresaUsuario.empresa_id == self.company_id,
                    EmpresaUsuario.usuario_id == self.applicant_id,
                )
                .count(),
                1,
            )
            self.assertEqual(
                db.query(Notificacion)
                .filter(
                    Notificacion.postulacion_id == self.application_id,
                    Notificacion.tipo == "POSTULACION_ESTADO",
                )
                .count(),
                1,
            )

    def test_terminal_application_states_reject_later_transitions(self):
        with SessionLocal() as db:
            hired = PostulacionService(db).update(
                self.application_id,
                UpdatePostulacionDTO(estado="contratado"),
                self.owner_a_id,
            )
            self.assertEqual(hired.estado, "contratado")

        with SessionLocal() as db:
            with self.assertRaises(ConflictError):
                PostulacionService(db).update(
                    self.application_id,
                    UpdatePostulacionDTO(estado="rechazada"),
                    self.owner_a_id,
                )
            with self.assertRaises(ConflictError):
                PostulacionService(db).update(
                    self.rejected_application_id,
                    UpdatePostulacionDTO(estado="vista"),
                    self.owner_a_id,
                )

        with SessionLocal() as db:
            self.assertEqual(
                db.get(Postulacion, self.application_id).estado,
                "contratado",
            )
            self.assertEqual(
                db.get(Postulacion, self.rejected_application_id).estado,
                "rechazada",
            )

    def test_company_creation_is_atomic_and_includes_owner(self):
        suffix = uuid4().hex
        with SessionLocal() as db:
            created = EmpresaService(db).create(
                CreateEmpresaDTO(nombre=f"Nueva empresa {suffix}"),
                self.collaborator_id,
            )
            self.company_ids.append(created.id)
            membership = db.get(
                EmpresaUsuario,
                (created.id, self.collaborator_id),
            )
            self.assertIsNotNone(membership)
            self.assertEqual(membership.rol, RolEmpresa.OWNER)

        failed_name = f"Empresa sin owner {suffix}"
        with SessionLocal() as db:
            missing_user_id = max(self.user_ids) + 1_000_000
            with self.assertRaises(IntegrityError):
                EmpresaRepository(db).create_with_owner(
                    CreateEmpresaDTO(nombre=failed_name),
                    missing_user_id,
                )
        with SessionLocal() as db:
            self.assertIsNone(
                db.query(Empresa).filter(Empresa.nombre == failed_name).first()
            )

    def test_last_owner_cannot_be_demoted_or_deleted(self):
        with SessionLocal() as db:
            EmpresaUsuarioService(db).delete(
                self.company_id,
                self.owner_b_id,
                self.owner_a_id,
            )

        for role in (RolEmpresa.RECRUITER, RolEmpresa.COLLABORATOR):
            with self.subTest(role=role), SessionLocal() as db:
                with self.assertRaises(ConflictError):
                    EmpresaUsuarioService(db).update(
                        self.company_id,
                        self.owner_a_id,
                        UpdateEmpresaUsuarioDTO(rol=role),
                        self.owner_a_id,
                    )

        with SessionLocal() as db:
            with self.assertRaises(ConflictError):
                EmpresaUsuarioService(db).delete(
                    self.company_id,
                    self.owner_a_id,
                    self.owner_a_id,
                )
        with SessionLocal() as db:
            owner = db.get(EmpresaUsuario, (self.company_id, self.owner_a_id))
            self.assertIsNotNone(owner)
            self.assertEqual(owner.rol, RolEmpresa.OWNER)
            self.assertEqual(
                db.query(EmpresaUsuario)
                .filter(
                    EmpresaUsuario.empresa_id == self.company_id,
                    EmpresaUsuario.rol == RolEmpresa.OWNER,
                )
                .count(),
                1,
            )

    def test_multiple_owners_allow_one_demotion_and_one_deletion(self):
        with SessionLocal() as db:
            demoted = EmpresaUsuarioService(db).update(
                self.company_id,
                self.owner_b_id,
                UpdateEmpresaUsuarioDTO(rol=RolEmpresa.RECRUITER),
                self.owner_a_id,
            )
            self.assertEqual(demoted.rol, RolEmpresa.RECRUITER)

        with SessionLocal() as db:
            promoted = EmpresaUsuarioService(db).update(
                self.company_id,
                self.recruiter_id,
                UpdateEmpresaUsuarioDTO(rol=RolEmpresa.OWNER),
                self.owner_a_id,
            )
            self.assertEqual(promoted.rol, RolEmpresa.OWNER)
            EmpresaUsuarioService(db).delete(
                self.company_id,
                self.owner_a_id,
                self.recruiter_id,
            )

        with SessionLocal() as db:
            self.assertIsNone(
                db.get(EmpresaUsuario, (self.company_id, self.owner_a_id))
            )
            remaining_owner = db.get(
                EmpresaUsuario,
                (self.company_id, self.recruiter_id),
            )
            self.assertEqual(remaining_owner.rol, RolEmpresa.OWNER)

    def test_only_owner_can_assign_roles_and_add_another_owner(self):
        for actor_id in (self.recruiter_id, self.collaborator_id):
            with self.subTest(actor_id=actor_id), SessionLocal() as db:
                with self.assertRaises(ForbiddenError):
                    EmpresaUsuarioService(db).update(
                        self.company_id,
                        self.owner_b_id,
                        UpdateEmpresaUsuarioDTO(rol=RolEmpresa.RECRUITER),
                        actor_id,
                    )

        with SessionLocal() as db:
            added = EmpresaUsuarioService(db).create(
                self.company_id,
                CreateEmpresaUsuarioDTO(
                    usuario_id=self.rejected_applicant_id,
                    rol=RolEmpresa.OWNER,
                ),
                self.owner_a_id,
            )
            self.assertEqual(added.rol, RolEmpresa.OWNER)
            promoted = EmpresaUsuarioService(db).update(
                self.company_id,
                self.recruiter_id,
                UpdateEmpresaUsuarioDTO(rol=RolEmpresa.OWNER),
                self.owner_a_id,
            )
            self.assertEqual(promoted.rol, RolEmpresa.OWNER)

        with SessionLocal() as db:
            self.assertEqual(
                db.get(EmpresaUsuario, (self.company_id, self.owner_a_id)).rol,
                RolEmpresa.OWNER,
            )
            self.assertEqual(
                db.get(EmpresaUsuario, (self.company_id, self.owner_b_id)).rol,
                RolEmpresa.OWNER,
            )

    def test_concurrent_owner_demotions_keep_one_owner(self):
        attempted = Event()
        finished = Event()
        with SessionLocal() as first_db:
            first_pid = first_db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            locked = EmpresaRepository(first_db).get_by_id_for_update(self.company_id)
            self.assertIsNotNone(locked)

            with ThreadPoolExecutor(max_workers=1) as executor:
                waiting = executor.submit(
                    self._member_update,
                    self.owner_b_id,
                    RolEmpresa.RECRUITER,
                    attempted=attempted,
                    finished=finished,
                )
                self.assertTrue(attempted.wait(timeout=3))
                self.assertFalse(finished.wait(timeout=0.2))
                first = EmpresaUsuarioService(first_db).update(
                    self.company_id,
                    self.owner_a_id,
                    UpdateEmpresaUsuarioDTO(rol=RolEmpresa.RECRUITER),
                    self.owner_a_id,
                )
                self.assertEqual(first.rol, RolEmpresa.RECRUITER)
                waiting_result, waiting_pid = waiting.result(timeout=5)

        self.assertNotEqual(first_pid, waiting_pid)
        self.assertEqual(waiting_result, "rejected")
        with SessionLocal() as db:
            owners = (
                db.query(EmpresaUsuario)
                .filter(
                    EmpresaUsuario.empresa_id == self.company_id,
                    EmpresaUsuario.rol == RolEmpresa.OWNER,
                )
                .all()
            )
            self.assertEqual([owner.usuario_id for owner in owners], [self.owner_b_id])

    def test_concurrent_owner_deletions_keep_one_owner(self):
        attempted = Event()
        finished = Event()
        with SessionLocal() as first_db:
            first_pid = first_db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            locked = EmpresaRepository(first_db).get_by_id_for_update(self.company_id)
            self.assertIsNotNone(locked)

            with ThreadPoolExecutor(max_workers=1) as executor:
                waiting = executor.submit(
                    self._member_delete,
                    self.owner_b_id,
                    attempted=attempted,
                    finished=finished,
                )
                self.assertTrue(attempted.wait(timeout=3))
                self.assertFalse(finished.wait(timeout=0.2))
                EmpresaUsuarioService(first_db).delete(
                    self.company_id,
                    self.owner_a_id,
                    self.owner_a_id,
                )
                waiting_result, waiting_pid = waiting.result(timeout=5)

        self.assertNotEqual(first_pid, waiting_pid)
        self.assertEqual(waiting_result, "rejected")
        with SessionLocal() as db:
            owners = (
                db.query(EmpresaUsuario)
                .filter(
                    EmpresaUsuario.empresa_id == self.company_id,
                    EmpresaUsuario.rol == RolEmpresa.OWNER,
                )
                .all()
            )
            self.assertEqual([owner.usuario_id for owner in owners], [self.owner_b_id])


if __name__ == "__main__":
    unittest.main()
