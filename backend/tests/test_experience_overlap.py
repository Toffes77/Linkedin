import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.app import app  # noqa: F401 - registra todos los modelos SQLAlchemy
from src.db.connection import SessionLocal, engine
from src.db.models.empresa_model import Empresa
from src.db.models.experiencia_model import Experiencia
from src.db.models.usuario_model import Usuario
from src.dtos.experiencia_dto import CreateExperienciaDTO, UpdateExperienciaDTO
from src.services.experiencia_service import ExperienciaService
from src.utils.errors import ConflictError, NotFoundError


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La garantía de solapamiento requiere PostgreSQL.",
)
class ExperienceOverlapTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        with SessionLocal() as db:
            self.user = Usuario(
                email=f"experience-{suffix}@example.com",
                nombre="Experience Owner",
                password_hash="not-used",
                headline="Experiencias",
                ciudad="Buenos Aires",
            )
            self.other_user = Usuario(
                email=f"experience-other-{suffix}@example.com",
                nombre="Other Owner",
                password_hash="not-used",
                headline="Experiencias",
                ciudad="Buenos Aires",
            )
            self.company = Empresa(nombre=f"Experience Company {suffix}")
            self.other_company = Empresa(nombre=f"Other Company {suffix}")
            db.add_all(
                [self.user, self.other_user, self.company, self.other_company]
            )
            db.commit()
            self.user_id = self.user.id
            self.other_user_id = self.other_user.id
            self.company_id = self.company.id
            self.other_company_id = self.other_company.id

    def tearDown(self):
        with SessionLocal() as db:
            db.query(Experiencia).filter(
                Experiencia.usuario_id.in_([self.user_id, self.other_user_id])
            ).delete(synchronize_session=False)
            db.query(Empresa).filter(
                Empresa.id.in_([self.company_id, self.other_company_id])
            ).delete(synchronize_session=False)
            db.query(Usuario).filter(
                Usuario.id.in_([self.user_id, self.other_user_id])
            ).delete(synchronize_session=False)
            db.commit()

    def _dto(
        self,
        *,
        user_id: int | None = None,
        company_id: int | None = None,
        start: date = date(2020, 1, 1),
        end: date | None = date(2020, 12, 31),
        position: str = "Developer",
    ) -> CreateExperienciaDTO:
        return CreateExperienciaDTO(
            usuario_id=user_id or self.user_id,
            empresa_id=company_id or self.company_id,
            puesto=position,
            desde=start,
            hasta=end,
        )

    def _create(self, **kwargs):
        with SessionLocal() as db:
            dto = self._dto(**kwargs)
            return ExperienciaService(db).create(dto, dto.usuario_id)

    def test_same_company_separate_periods_are_allowed(self):
        self._create(end=date(2020, 12, 31))
        second = self._create(
            start=date(2021, 1, 1),
            end=date(2021, 12, 31),
        )
        self.assertIsNotNone(second.id)

    def test_same_company_partial_overlap_is_rejected(self):
        self._create(end=date(2022, 1, 1))
        with self.assertRaises(ConflictError):
            self._create(start=date(2021, 6, 1), end=date(2023, 1, 1))

    def test_same_company_contained_period_is_rejected(self):
        self._create(start=date(2020, 1, 1), end=date(2024, 1, 1))
        with self.assertRaises(ConflictError):
            self._create(start=date(2021, 1, 1), end=date(2022, 1, 1))

    def test_open_period_overlaps_every_later_period_in_same_company(self):
        self._create(start=date(2020, 1, 1), end=None)
        with self.assertRaises(ConflictError):
            self._create(start=date(2023, 1, 1), end=date(2024, 1, 1))

    def test_equal_boundary_is_an_overlap_for_closed_date_intervals(self):
        self._create(end=date(2024, 5, 1))
        with self.assertRaises(ConflictError):
            self._create(start=date(2024, 5, 1), end=date(2025, 1, 1))

    def test_different_companies_may_have_identical_periods(self):
        first = self._create()
        second = self._create(company_id=self.other_company_id)
        self.assertNotEqual(first.id, second.id)

    def test_different_users_may_overlap_at_same_company(self):
        self._create()
        second = self._create(user_id=self.other_user_id)
        self.assertIsNotNone(second.id)

    def test_update_excludes_the_experience_itself(self):
        created = self._create()
        with SessionLocal() as db:
            updated = ExperienciaService(db).update(
                created.id,
                UpdateExperienciaDTO(puesto="Senior Developer"),
                self.user_id,
            )
        self.assertEqual(updated.puesto, "Senior Developer")

    def test_update_to_overlapping_period_is_rejected(self):
        first = self._create(end=date(2020, 12, 31))
        second = self._create(
            start=date(2022, 1, 1),
            end=date(2022, 12, 31),
        )
        with SessionLocal() as db:
            with self.assertRaises(ConflictError):
                ExperienciaService(db).update(
                    second.id,
                    UpdateExperienciaDTO(desde=date(2020, 6, 1)),
                    self.user_id,
                )
        with SessionLocal() as db:
            self.assertEqual(db.get(Experiencia, first.id).desde, date(2020, 1, 1))
            self.assertEqual(db.get(Experiencia, second.id).desde, date(2022, 1, 1))

    def test_missing_company_and_invalid_dates_remain_rejected(self):
        with SessionLocal() as db:
            with self.assertRaises(NotFoundError):
                ExperienciaService(db).create(
                    self._dto(company_id=self.other_company_id + 1_000_000),
                    self.user_id,
                )
        with self.assertRaises(ValidationError):
            self._dto(start=date(2024, 2, 1), end=date(2024, 1, 1))

    def test_database_constraint_blocks_service_bypass(self):
        with SessionLocal() as db:
            db.add(
                Experiencia(
                    usuario_id=self.user_id,
                    empresa_id=self.company_id,
                    puesto="First",
                    desde=date(2020, 1, 1),
                    hasta=date(2022, 1, 1),
                )
            )
            db.commit()
            db.add(
                Experiencia(
                    usuario_id=self.user_id,
                    empresa_id=self.company_id,
                    puesto="Overlapping",
                    desde=date(2021, 1, 1),
                    hasta=date(2023, 1, 1),
                )
            )
            with self.assertRaises(IntegrityError) as raised:
                db.commit()
            db.rollback()
        self.assertEqual(
            raised.exception.orig.diag.constraint_name,
            "exclude_experiencia_usuario_empresa_periodo",
        )

    def test_concurrent_overlapping_creations_leave_only_one_row(self):
        barrier = Barrier(2)

        def create_concurrently(start: date, end: date) -> tuple[str, int]:
            with SessionLocal() as db:
                backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
                service = ExperienciaService(db)
                barrier.wait(timeout=5)
                try:
                    service.create(
                        self._dto(start=start, end=end),
                        self.user_id,
                    )
                    outcome = "created"
                except ConflictError:
                    outcome = "conflict"
                return outcome, backend_pid

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(
                create_concurrently,
                date(2020, 1, 1),
                date(2022, 1, 1),
            )
            second = executor.submit(
                create_concurrently,
                date(2021, 1, 1),
                date(2023, 1, 1),
            )
            results = [first.result(timeout=10), second.result(timeout=10)]

        self.assertEqual({outcome for outcome, _ in results}, {"created", "conflict"})
        self.assertEqual(len({pid for _, pid in results}), 2)
        with SessionLocal() as db:
            count = db.query(Experiencia).filter(
                Experiencia.usuario_id == self.user_id,
                Experiencia.empresa_id == self.company_id,
            ).count()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
