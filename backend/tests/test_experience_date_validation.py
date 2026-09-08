import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from src.dtos.experiencia_dto import CreateExperienciaDTO, UpdateExperienciaDTO
from src.schemas.experiencia_schema import (
    CreateExperienciaSchema,
    UpdateExperienciaSchema,
)


class ExperienceDateValidationTests(unittest.TestCase):
    def setUp(self):
        self.today = date.today()
        self.past = self.today - timedelta(days=1)
        self.future = self.today + timedelta(days=1)

    def test_create_accepts_today_past_end_today_and_current_experience(self):
        CreateExperienciaSchema(
            empresa_id=1,
            puesto="Developer",
            desde=self.today,
            hasta=self.today,
        )
        CreateExperienciaSchema(
            empresa_id=1,
            puesto="Developer",
            desde=self.past,
            hasta=self.today,
        )
        CreateExperienciaDTO(
            usuario_id=1,
            empresa_id=1,
            puesto="Developer",
            desde=self.past,
            hasta=None,
        )

    def test_create_rejects_future_dates_and_end_before_start(self):
        with self.assertRaises(ValidationError):
            CreateExperienciaSchema(
                empresa_id=1,
                puesto="Developer",
                desde=self.future,
            )
        with self.assertRaises(ValidationError):
            CreateExperienciaSchema(
                empresa_id=1,
                puesto="Developer",
                desde=self.past,
                hasta=self.future,
            )
        with self.assertRaises(ValidationError):
            CreateExperienciaDTO(
                usuario_id=1,
                empresa_id=1,
                puesto="Developer",
                desde=self.today,
                hasta=self.past,
            )

    def test_update_rejects_future_dates_and_end_before_start_when_both_are_sent(self):
        with self.assertRaises(ValidationError):
            UpdateExperienciaSchema(desde=self.future)
        with self.assertRaises(ValidationError):
            UpdateExperienciaSchema(hasta=self.future)
        with self.assertRaises(ValidationError):
            UpdateExperienciaDTO(desde=self.today, hasta=self.past)


if __name__ == "__main__":
    unittest.main()
