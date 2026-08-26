import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, get_db
from src.db.models.conexiones_model import Conexion
from src.db.models.publicacion_model import Publicacion
from src.db.models.seguimiento_model import Seguimiento
from src.db.models.usuario_model import Usuario
from src.dtos.conexiones_dto import ResumenRedResponseDTO
from src.dtos.seguimiento_dto import EstadoSeguimientoResponseDTO
from src.mappers.conexion_mapper import ConexionMapper
from src.mappers.seguimiento_mapper import SeguimientoMapper
from src.middlewares.auth_middleware import get_current_user
from src.repositories.publicacion_repository import PublicacionRepository
from src.services.conexion_service import ConexionService
from src.services.feed_service import FeedService
from src.services.publicacion_service import PublicacionService
from src.services.seguimiento_service import SeguimientoService
from src.utils.errors import ConflictError


def post(post_id: int, author_id: int, minutes: int):
    return SimpleNamespace(
        id=post_id,
        autor_id=author_id,
        texto=f"Post {post_id}",
        fecha=datetime(2026, 1, 1) + timedelta(minutes=minutes),
    )


class GlobalFeedRepositoryTests(unittest.TestCase):
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
        self.viewer = self._user(1, "viewer@example.com", "Viewer")
        followed = self._user(2, "followed@example.com", "Seguido")
        connected = self._user(3, "connected@example.com", "Conexión")
        unrelated = self._user(4, "unrelated@example.com", "Sin relación")
        self.db.add_all([self.viewer, followed, connected, unrelated])
        self.db.flush()
        self.db.add_all(
            [
                Seguimiento(seguidor_id=self.viewer.id, seguido_id=followed.id),
                Conexion(
                    usuario_a=self.viewer.id,
                    usuario_b=connected.id,
                    estado="aceptada",
                ),
            ]
        )

        base_date = datetime(2026, 1, 1, 8, 0, 0)
        self.db.add_all(
            [
                Publicacion(
                    id=101,
                    autor_id=followed.id,
                    texto="Publicación seguida más antigua",
                    fecha=base_date,
                ),
                Publicacion(
                    id=102,
                    autor_id=connected.id,
                    texto="Publicación de conexión",
                    fecha=base_date + timedelta(hours=1),
                ),
                Publicacion(
                    id=103,
                    autor_id=unrelated.id,
                    texto="Publicación sin relación",
                    fecha=base_date + timedelta(hours=2),
                ),
                Publicacion(
                    id=104,
                    autor_id=self.viewer.id,
                    texto="Publicación propia",
                    fecha=base_date + timedelta(hours=3),
                ),
                Publicacion(
                    id=105,
                    autor_id=followed.id,
                    texto="Empate menor ID",
                    fecha=base_date + timedelta(hours=4),
                ),
                Publicacion(
                    id=106,
                    autor_id=unrelated.id,
                    texto="Empate mayor ID",
                    fecha=base_date + timedelta(hours=4),
                ),
            ]
        )
        self.db.commit()
        self.repository = PublicacionRepository(self.db)

    def tearDown(self):
        self.db.rollback()
        self.db.query(Publicacion).delete()
        self.db.query(Seguimiento).delete()
        self.db.query(Conexion).delete()
        self.db.query(Usuario).delete()
        self.db.commit()
        self.db.close()

    @staticmethod
    def _user(user_id: int, email: str, name: str) -> Usuario:
        return Usuario(
            id=user_id,
            email=email,
            nombre=name,
            password_hash="not-used",
            headline="Prueba de feed",
            ciudad="Buenos Aires",
        )

    def ids(self, limit: int, offset: int) -> list[int]:
        return [
            publication.id
            for publication in self.repository.get_feed(limit, offset)
        ]

    def test_all_posts_compete_only_by_date_regardless_of_social_relationship(self):
        self.assertEqual(
            self.ids(limit=20, offset=0),
            [106, 105, 104, 103, 102, 101],
        )

    def test_equal_dates_use_descending_id_as_stable_tiebreaker(self):
        self.assertEqual(self.ids(limit=2, offset=0), [106, 105])

    def test_pages_use_limit_and_offset_without_duplicates(self):
        first_page = self.ids(limit=2, offset=0)
        second_page = self.ids(limit=2, offset=2)
        third_page = self.ids(limit=2, offset=4)

        self.assertEqual(first_page, [106, 105])
        self.assertEqual(second_page, [104, 103])
        self.assertEqual(third_page, [102, 101])
        self.assertEqual(
            len(set(first_page + second_page + third_page)),
            6,
        )

    def test_empty_feed_returns_an_empty_list(self):
        self.db.query(Publicacion).delete()
        self.db.commit()

        self.assertEqual(self.ids(limit=20, offset=0), [])


class SocialFeedTests(unittest.TestCase):
    def test_author_posts_are_paginated_and_delegated_to_repository(self):
        service = PublicacionService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=7)
        service.repository = Mock()
        service.repository.get_by_autor.return_value = [post(3, 7, 3)]

        result = service.get_by_autor(7, limit=20, offset=40)

        service.repository.get_by_autor.assert_called_once_with(7, 20, 40)
        self.assertEqual([item.autor_id for item in result], [7])

    def test_author_without_posts_returns_empty_list(self):
        service = PublicacionService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=7)
        service.repository = Mock()
        service.repository.get_by_autor.return_value = []

        self.assertEqual(service.get_by_autor(7), [])

    def test_network_summary_counts_each_concept_independently(self):
        service = ConexionService(Mock())
        service.repository = Mock()
        service.seguimiento_repository = Mock()
        service.repository.count_pending_sent.return_value = 3
        service.repository.count_accepted_by_user.return_value = 24
        service.seguimiento_repository.count_following.return_value = 18

        self.assertEqual(
            service.get_resumen_red(9).model_dump(),
            {"invitaciones_enviadas": 3, "contactos": 24, "siguiendo": 18},
        )
        service.repository.count_pending_sent.assert_called_once_with(9)
        service.repository.count_accepted_by_user.assert_called_once_with(9)
        service.seguimiento_repository.count_following.assert_called_once_with(9)

    def test_network_summary_mapper_converts_dto_to_schema(self):
        schema = ConexionMapper.to_resumen_response_schema(
            ResumenRedResponseDTO(
                invitaciones_enviadas=3,
                contactos=24,
                siguiendo=18,
            )
        )

        self.assertEqual(
            schema.model_dump(),
            {"invitaciones_enviadas": 3, "contactos": 24, "siguiendo": 18},
        )

    def test_network_summary_endpoint_returns_200_instead_of_500(self):
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=9)
        try:
            with patch(
                "src.routers.conexion_router.ConexionService.get_resumen_red",
                return_value=ResumenRedResponseDTO(
                    invitaciones_enviadas=0,
                    contactos=0,
                    siguiendo=3,
                ),
            ):
                response = TestClient(app).get("/api/conexiones/resumen")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json(),
                {"invitaciones_enviadas": 0, "contactos": 0, "siguiendo": 3},
            )
        finally:
            app.dependency_overrides.clear()

    def test_follow_is_idempotent_and_unfollow_deletes_existing_relation(self):
        service = SeguimientoService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=2)
        service.notificacion_service = Mock()
        existing = SimpleNamespace(seguidor_id=1, seguido_id=2, fecha=datetime.now())
        service.repository = Mock()
        service.repository.get.return_value = existing

        result = service.follow(1, 2)
        service.repository.create.assert_not_called()
        service.notificacion_service.create_many.assert_not_called()
        self.assertEqual(result.seguido_id, 2)
        service.unfollow(1, 2)
        service.repository.delete.assert_called_once_with(existing)
        service.notificacion_service.create_many.assert_not_called()

    def test_follow_status_mapper_converts_dto_to_schema(self):
        schema = SeguimientoMapper.to_status_schema(
            EstadoSeguimientoResponseDTO(siguiendo=True)
        )

        self.assertEqual(schema.model_dump(), {"siguiendo": True})

    def test_new_follow_creates_one_unread_notification_for_followed_user(self):
        db = Mock()
        service = SeguimientoService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.side_effect = lambda user_id: {
            1: SimpleNamespace(id=1, nombre="Juan Cruz"),
            2: SimpleNamespace(id=2, nombre="Pedro"),
        }.get(user_id)
        service.repository = Mock()
        service.repository.get.return_value = None
        created_follow = SimpleNamespace(
            seguidor_id=1,
            seguido_id=2,
            fecha=datetime.now(),
        )
        service.repository.create.return_value = created_follow
        service.notificacion_service = Mock()

        result = service.follow(1, 2)

        service.repository.create.assert_called_once_with(1, 2, commit=False)
        notifications = service.notificacion_service.create_many.call_args.args[0]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].usuario_id, 2)
        self.assertEqual(notifications[0].usuario_origen_id, 1)
        self.assertEqual(notifications[0].tipo, "NUEVO_SEGUIDOR")
        self.assertEqual(notifications[0].mensaje, "Juan Cruz empezó a seguirte.")
        service.notificacion_service.create_many.assert_called_once_with(
            notifications,
            commit=False,
        )
        db.commit.assert_called_once_with()
        db.refresh.assert_called_once_with(created_follow)
        db.rollback.assert_not_called()
        self.assertEqual(result.seguido_id, 2)

    def test_notification_failure_rolls_back_new_follow(self):
        db = Mock()
        service = SeguimientoService(db)
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.side_effect = lambda user_id: {
            1: SimpleNamespace(id=1, nombre="Juan Cruz"),
            2: SimpleNamespace(id=2, nombre="Pedro"),
        }.get(user_id)
        service.repository = Mock()
        service.repository.get.return_value = None
        service.repository.create.return_value = SimpleNamespace(
            seguidor_id=1,
            seguido_id=2,
            fecha=datetime.now(),
        )
        service.notificacion_service = Mock()
        service.notificacion_service.create_many.side_effect = RuntimeError(
            "forced notification failure"
        )

        with self.assertRaisesRegex(RuntimeError, "forced notification failure"):
            service.follow(1, 2)

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()

    def test_cannot_follow_self(self):
        service = SeguimientoService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.repository = Mock()

        with self.assertRaises(ConflictError):
            service.follow(1, 1)

    def test_feed_requests_one_global_page_without_social_priority(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_feed.return_value = [
            post(20, 4, 10),
            post(21, 2, 9),
        ]

        result = service.get_feed(1, page=1, page_size=2)

        self.assertEqual([item.id for item in result], [20, 21])
        service.publicacion_repository.get_feed.assert_called_once_with(
            limit=2,
            offset=0,
        )
        self.assertFalse(hasattr(service, "seguimiento_repository"))

    def test_feed_second_page_translates_to_database_offset(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_feed.return_value = [
            post(30, 4, 8),
            post(31, 2, 7),
        ]

        result = service.get_feed(1, page=2, page_size=2)

        self.assertEqual([item.id for item in result], [30, 31])
        service.publicacion_repository.get_feed.assert_called_once_with(
            limit=2,
            offset=2,
        )

    def test_feed_empty_page_still_uses_requested_page_size(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_feed.return_value = []

        result = service.get_feed(1, page=3, page_size=7)

        self.assertEqual(result, [])
        service.publicacion_repository.get_feed.assert_called_once_with(
            limit=7,
            offset=14,
        )

    def test_feed_endpoint_still_requires_authentication(self):
        app.dependency_overrides.clear()
        try:
            response = TestClient(app).get("/api/feed")
            self.assertEqual(response.status_code, 401)
        finally:
            app.dependency_overrides.clear()

    def test_feed_endpoint_preserves_page_and_page_size_contract(self):
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=9)
        try:
            with patch(
                "src.routers.feed_router.FeedService.get_feed",
                return_value=[post(50, 4, 1)],
            ) as get_feed:
                response = TestClient(app).get(
                    "/api/feed",
                    params={"page": 2, "page_size": 7},
                )

            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()[0]["id"], 50)
            get_feed.assert_called_once_with(9, 2, 7)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
