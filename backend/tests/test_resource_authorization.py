import unittest
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.experiencia_model import Experiencia
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.usuario_model import Usuario
from src.dtos.experiencia_dto import UpdateExperienciaDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.experiencia_service import ExperienciaService
from src.utils.errors import ForbiddenError


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Las pruebas de autorización requieren la PostgreSQL configurada.",
)
class ResourceAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

        suffix = uuid4().hex
        self.applicant_a = self._user(f"applicant-a-{suffix}@example.com", "A")
        self.applicant_b = self._user(f"applicant-b-{suffix}@example.com", "B")
        self.owner = self._user(f"owner-{suffix}@example.com", "Owner")
        self.recruiter = self._user(f"recruiter-{suffix}@example.com", "Recruiter")
        self.collaborator = self._user(
            f"collaborator-{suffix}@example.com",
            "Collaborator",
        )
        self.outsider = self._user(f"outsider-{suffix}@example.com", "Outsider")
        self.other_owner = self._user(
            f"other-owner-{suffix}@example.com",
            "Other owner",
        )
        self.other_recruiter = self._user(
            f"other-recruiter-{suffix}@example.com",
            "Other recruiter",
        )
        self.company = Empresa(nombre=f"Empresa autorización {suffix}")
        self.other_company = Empresa(nombre=f"Otra empresa autorización {suffix}")
        self.db.add_all(
            [
                self.applicant_a,
                self.applicant_b,
                self.owner,
                self.recruiter,
                self.collaborator,
                self.outsider,
                self.other_owner,
                self.other_recruiter,
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
                    usuario_id=self.other_owner.id,
                    rol=RolEmpresa.OWNER,
                ),
                EmpresaUsuario(
                    empresa_id=self.other_company.id,
                    usuario_id=self.other_recruiter.id,
                    rol=RolEmpresa.RECRUITER,
                ),
            ]
        )
        self.offer = Oferta(
            empresa_id=self.company.id,
            titulo="Oferta privada",
            descripcion="Solo para pruebas de autorización.",
            publicada=True,
        )
        self.other_offer = Oferta(
            empresa_id=self.other_company.id,
            titulo="Otra oferta privada",
            descripcion="Solo para pruebas de autorización.",
            publicada=True,
        )
        self.db.add_all([self.offer, self.other_offer])
        self.db.flush()

        self.application_a = Postulacion(
            oferta_id=self.offer.id,
            usuario_id=self.applicant_a.id,
        )
        self.application_b = Postulacion(
            oferta_id=self.offer.id,
            usuario_id=self.applicant_b.id,
        )
        self.db.add_all([self.application_a, self.application_b])
        self.db.flush()
        self.db.commit()

        self.current_user = self.applicant_a
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
            headline="Perfil de prueba",
            ciudad="Buenos Aires",
        )

    @staticmethod
    def _experience_payload(
        company_id: int,
        *,
        start: str = "2023-01-01",
        end: str | None = "2023-12-31",
        position: str = "Developer",
    ) -> dict:
        return {
            "empresa_id": company_id,
            "puesto": position,
            "desde": start,
            "hasta": end,
        }

    def _without_auth_override(self, method: str, path: str, **kwargs):
        app.dependency_overrides.pop(get_current_user)
        try:
            return self.client.request(method, path, **kwargs)
        finally:
            app.dependency_overrides[get_current_user] = lambda: self.current_user

    def test_authenticated_user_creates_own_experience_and_profile_stays_public(self):
        payload = self._experience_payload(self.company.id)
        payload["usuario_id"] = self.applicant_b.id
        created = self.client.post(
            f"/api/usuarios/{self.applicant_a.id}/experiencias",
            json=payload,
        )

        self.assertEqual(created.status_code, 201, created.text)
        stored = self.db.get(Experiencia, created.json()["id"])
        self.assertIsNotNone(stored)
        self.assertEqual(stored.usuario_id, self.applicant_a.id)

        app.dependency_overrides.pop(get_current_user)
        try:
            public_profile = self.client.get(f"/api/usuarios/{self.applicant_a.id}")
        finally:
            app.dependency_overrides[get_current_user] = lambda: self.current_user

        self.assertEqual(public_profile.status_code, 200, public_profile.text)
        self.assertIn(
            stored.id,
            [experience["id"] for experience in public_profile.json()["experiencias"]],
        )

    def test_unauthenticated_user_cannot_create_experience(self):
        count_before = self.db.query(Experiencia).count()

        response = self._without_auth_override(
            "POST",
            f"/api/usuarios/{self.applicant_a.id}/experiencias",
            json=self._experience_payload(self.company.id),
        )

        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self.db.query(Experiencia).count(), count_before)

    def test_user_cannot_create_experience_for_another_user(self):
        count_before = (
            self.db.query(Experiencia)
            .filter(Experiencia.usuario_id == self.applicant_b.id)
            .count()
        )

        response = self.client.post(
            f"/api/usuarios/{self.applicant_b.id}/experiencias",
            json=self._experience_payload(self.company.id),
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(
            self.db.query(Experiencia)
            .filter(Experiencia.usuario_id == self.applicant_b.id)
            .count(),
            count_before,
        )

    def test_experience_service_allows_own_update_and_rejects_foreign_update(self):
        own = Experiencia(
            usuario_id=self.applicant_a.id,
            empresa_id=self.company.id,
            puesto="Junior",
            desde=date(2020, 1, 1),
            hasta=date(2020, 12, 31),
        )
        foreign = Experiencia(
            usuario_id=self.applicant_b.id,
            empresa_id=self.company.id,
            puesto="Original",
            desde=date(2020, 1, 1),
            hasta=date(2020, 12, 31),
        )
        self.db.add_all([own, foreign])
        self.db.commit()
        service = ExperienciaService(self.db)

        updated = service.update(
            own.id,
            UpdateExperienciaDTO(puesto="Senior"),
            self.applicant_a.id,
        )
        self.assertEqual(updated.puesto, "Senior")

        with self.assertRaises(ForbiddenError):
            service.update(
                foreign.id,
                UpdateExperienciaDTO(puesto="Alterado"),
                self.applicant_a.id,
            )

        self.db.expire(foreign)
        self.assertEqual(foreign.puesto, "Original")

    def test_experience_service_allows_own_delete_and_rejects_foreign_delete(self):
        own = Experiencia(
            usuario_id=self.applicant_a.id,
            empresa_id=self.company.id,
            puesto="Propia",
            desde=date(2021, 1, 1),
            hasta=date(2021, 12, 31),
        )
        foreign = Experiencia(
            usuario_id=self.applicant_b.id,
            empresa_id=self.company.id,
            puesto="Ajena",
            desde=date(2021, 1, 1),
            hasta=date(2021, 12, 31),
        )
        self.db.add_all([own, foreign])
        self.db.commit()
        own_id = own.id
        foreign_id = foreign.id
        service = ExperienciaService(self.db)

        service.delete(own_id, self.applicant_a.id)
        self.assertIsNone(self.db.get(Experiencia, own_id))

        with self.assertRaises(ForbiddenError):
            service.delete(foreign_id, self.applicant_a.id)

        self.assertIsNotNone(self.db.get(Experiencia, foreign_id))

    def test_experience_date_company_and_overlap_validations_remain_active(self):
        invalid_dates = self.client.post(
            f"/api/usuarios/{self.applicant_a.id}/experiencias",
            json=self._experience_payload(
                self.company.id,
                start="2024-12-31",
                end="2024-01-01",
            ),
        )
        self.assertEqual(invalid_dates.status_code, 422, invalid_dates.text)

        missing_company_id = max(self.company.id, self.other_company.id) + 1_000_000
        missing_company = self.client.post(
            f"/api/usuarios/{self.applicant_a.id}/experiencias",
            json=self._experience_payload(missing_company_id),
        )
        self.assertEqual(missing_company.status_code, 404, missing_company.text)

        first = self.client.post(
            f"/api/usuarios/{self.applicant_a.id}/experiencias",
            json=self._experience_payload(
                self.company.id,
                start="2024-01-01",
                end="2024-12-31",
            ),
        )
        self.assertEqual(first.status_code, 201, first.text)
        count_after_first = (
            self.db.query(Experiencia)
            .filter(Experiencia.usuario_id == self.applicant_a.id)
            .count()
        )

        overlap = self.client.post(
            f"/api/usuarios/{self.applicant_a.id}/experiencias",
            json=self._experience_payload(
                self.company.id,
                start="2024-06-01",
                end="2025-01-01",
            ),
        )
        self.assertEqual(overlap.status_code, 409, overlap.text)
        self.assertEqual(
            self.db.query(Experiencia)
            .filter(Experiencia.usuario_id == self.applicant_a.id)
            .count(),
            count_after_first,
        )

    def test_applicant_can_read_own_application_but_not_another_by_id(self):
        own = self.client.get(f"/api/postulaciones/{self.application_a.id}")
        foreign = self.client.get(f"/api/postulaciones/{self.application_b.id}")

        self.assertEqual(own.status_code, 200, own.text)
        self.assertEqual(own.json()["usuario_id"], self.applicant_a.id)
        self.assertEqual(foreign.status_code, 403, foreign.text)
        self.assertNotIn("oferta_titulo", foreign.json())

    def test_unauthenticated_user_cannot_read_application_by_id(self):
        response = self._without_auth_override(
            "GET",
            f"/api/postulaciones/{self.application_a.id}",
        )

        self.assertEqual(response.status_code, 401, response.text)

    def test_correct_company_owner_and_recruiter_can_read_application_by_id(self):
        for manager in (self.owner, self.recruiter):
            with self.subTest(role=manager.nombre):
                self.current_user = manager
                response = self.client.get(
                    f"/api/postulaciones/{self.application_a.id}"
                )
                self.assertEqual(response.status_code, 200, response.text)

    def test_wrong_company_managers_cannot_read_application_by_id(self):
        for manager in (self.other_owner, self.other_recruiter):
            with self.subTest(role=manager.nombre):
                self.current_user = manager
                response = self.client.get(
                    f"/api/postulaciones/{self.application_a.id}"
                )
                self.assertEqual(response.status_code, 403, response.text)

    def test_collaborator_and_outsider_cannot_read_application_by_id(self):
        for user in (self.collaborator, self.outsider):
            with self.subTest(user=user.nombre):
                self.current_user = user
                response = self.client.get(
                    f"/api/postulaciones/{self.application_a.id}"
                )
                self.assertEqual(response.status_code, 403, response.text)

    def test_user_application_listing_is_restricted_to_current_user(self):
        own = self.client.get(
            f"/api/usuarios/{self.applicant_a.id}/postulaciones"
        )
        foreign = self.client.get(
            f"/api/usuarios/{self.applicant_b.id}/postulaciones"
        )

        self.assertEqual(own.status_code, 200, own.text)
        self.assertEqual(
            [application["usuario_id"] for application in own.json()],
            [self.applicant_a.id],
        )
        self.assertEqual(foreign.status_code, 403, foreign.text)

    def test_unauthenticated_user_cannot_list_applications_by_user(self):
        response = self._without_auth_override(
            "GET",
            f"/api/usuarios/{self.applicant_a.id}/postulaciones",
        )

        self.assertEqual(response.status_code, 401, response.text)

    def test_correct_company_owner_and_recruiter_can_list_offer_applications(self):
        for manager in (self.owner, self.recruiter):
            with self.subTest(role=manager.nombre):
                self.current_user = manager
                response = self.client.get(
                    f"/api/ofertas/{self.offer.id}/postulaciones"
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()), 2)

    def test_unauthorized_roles_cannot_list_offer_applications(self):
        unauthorized = (
            self.applicant_a,
            self.collaborator,
            self.outsider,
            self.other_owner,
            self.other_recruiter,
        )
        for user in unauthorized:
            with self.subTest(user=user.nombre):
                self.current_user = user
                response = self.client.get(
                    f"/api/ofertas/{self.offer.id}/postulaciones"
                )
                self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
