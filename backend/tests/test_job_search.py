import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, get_db
from src.db.models.empresa_model import Empresa
from src.db.models.oferta_model import Oferta
from src.dtos.oferta_dto import OfertaResponseDTO
from src.repositories.oferta_repository import OfertaRepository
from src.services.oferta_service import OfertaService


class JobSearchRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.db: Session = self.SessionLocal()
        company = Empresa(nombre="Empresa de pruebas")
        self.db.add(company)
        self.db.flush()
        self.db.add_all(
            [
                Oferta(
                    empresa_id=company.id,
                    titulo="Desarrollador Backend",
                    descripcion="API y PostgreSQL",
                    publicada=True,
                ),
                Oferta(
                    empresa_id=company.id,
                    titulo="Desarrollador Python",
                    descripcion="Servicios web",
                    publicada=True,
                ),
                Oferta(
                    empresa_id=company.id,
                    titulo="DESARROLLADOR Frontend Senior",
                    descripcion="React",
                    publicada=True,
                ),
                Oferta(
                    empresa_id=company.id,
                    titulo="Analista funcional",
                    descripcion="Buscamos Desarrollador con experiencia",
                    publicada=True,
                ),
                Oferta(
                    empresa_id=company.id,
                    titulo="Desarrollador Mobile",
                    descripcion="Aplicaciones móviles",
                    publicada=False,
                ),
            ]
        )
        self.db.commit()
        self.repository = OfertaRepository(self.db)

    def tearDown(self):
        self.db.rollback()
        self.db.query(Oferta).delete()
        self.db.query(Empresa).delete()
        self.db.commit()
        self.db.close()

    def titles(self, q: str | None = None) -> list[str]:
        return [oferta.titulo for oferta in self.repository.get_publicadas(q)]

    def test_missing_query_keeps_the_normal_published_list(self):
        self.assertEqual(
            self.titles(),
            [
                "Desarrollador Backend",
                "Desarrollador Python",
                "DESARROLLADOR Frontend Senior",
                "Analista funcional",
            ],
        )

    def test_exact_word_matches_only_titles(self):
        self.assertEqual(
            self.titles("Desarrollador"),
            [
                "Desarrollador Backend",
                "Desarrollador Python",
                "DESARROLLADOR Frontend Senior",
            ],
        )

    def test_exact_title_match(self):
        self.assertEqual(self.titles("Analista funcional"), ["Analista funcional"])

    def test_partial_match(self):
        self.assertEqual(
            self.titles("desarroll"),
            [
                "Desarrollador Backend",
                "Desarrollador Python",
                "DESARROLLADOR Frontend Senior",
            ],
        )

    def test_search_is_case_insensitive(self):
        self.assertEqual(
            self.titles("desarrollador"),
            self.titles("DESARROLLADOR"),
        )

    def test_no_results_returns_an_empty_list(self):
        self.assertEqual(self.titles("zzzzzzz"), [])

    def test_title_filter_is_applied_before_the_query_is_materialized(self):
        db = Mock()
        query = Mock()
        db.query.return_value = query
        query.filter.return_value = query
        query.all.return_value = []

        OfertaRepository(db).get_publicadas("Desarrollador")

        self.assertEqual(query.filter.call_count, 2)
        query.all.assert_called_once_with()
        self.assertEqual(
            [method_call[0] for method_call in query.method_calls],
            ["filter", "filter", "all"],
        )


class JobSearchServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = OfertaService(Mock())
        self.service.repository = Mock()
        self.service.repository.get_publicadas.return_value = []

    def test_empty_query_uses_the_unfiltered_repository_query(self):
        self.service.get_publicadas("")
        self.service.repository.get_publicadas.assert_called_once_with(None)

    def test_whitespace_only_query_uses_the_unfiltered_repository_query(self):
        self.service.get_publicadas("   ")
        self.service.repository.get_publicadas.assert_called_once_with(None)

    def test_query_is_trimmed_before_filtering(self):
        self.service.get_publicadas("   Desarrollador   ")
        self.service.repository.get_publicadas.assert_called_once_with("Desarrollador")


class JobSearchEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_db] = lambda: Mock()
        self.offer = OfertaResponseDTO(
            id=1,
            empresa_id=2,
            titulo="Desarrollador Backend",
            descripcion="API y PostgreSQL",
            publicada=True,
            fecha_publicacion=datetime(2026, 8, 22, 12, 0, 0),
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_endpoint_without_q_preserves_the_existing_request(self):
        with patch(
            "src.routers.oferta_router.OfertaService.get_publicadas",
            return_value=[self.offer],
        ) as get_publicadas:
            response = TestClient(app).get("/api/ofertas/publicadas")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["titulo"], "Desarrollador Backend")
        get_publicadas.assert_called_once_with(None)

    def test_endpoint_forwards_q_to_the_service(self):
        with patch(
            "src.routers.oferta_router.OfertaService.get_publicadas",
            return_value=[self.offer],
        ) as get_publicadas:
            response = TestClient(app).get(
                "/api/ofertas/publicadas",
                params={"q": "Desarrollador"},
            )

        self.assertEqual(response.status_code, 200)
        get_publicadas.assert_called_once_with("Desarrollador")


if __name__ == "__main__":
    unittest.main()
