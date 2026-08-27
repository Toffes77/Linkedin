import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, engine, get_db
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
        general_authors = [
            self._user(
                user_id,
                f"general-{user_id}@example.com",
                f"General {user_id}",
            )
            for user_id in range(4, 11)
        ]
        self.db.add_all([self.viewer, followed, connected, *general_authors])
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

        base_date = datetime(2026, 1, 1, 0, 0, 0)
        self.db.add_all(
            [
                Publicacion(
                    id=201,
                    autor_id=4,
                    texto="General frecuente más reciente",
                    fecha=base_date + timedelta(hours=20),
                ),
                Publicacion(
                    id=202,
                    autor_id=4,
                    texto="General frecuente segunda",
                    fecha=base_date + timedelta(hours=19),
                ),
                Publicacion(
                    id=203,
                    autor_id=4,
                    texto="General frecuente excluida",
                    fecha=base_date + timedelta(hours=18),
                ),
                *[
                    Publicacion(
                        id=204 + index,
                        autor_id=5 + index,
                        texto=f"General {5 + index}",
                        fecha=base_date + timedelta(hours=17 - index),
                    )
                    for index in range(6)
                ],
                Publicacion(
                    id=210,
                    autor_id=self.viewer.id,
                    texto="Publicación propia",
                    fecha=base_date + timedelta(hours=11),
                ),
                Publicacion(
                    id=211,
                    autor_id=connected.id,
                    texto="Conexión reciente",
                    fecha=base_date + timedelta(hours=10),
                ),
                Publicacion(
                    id=212,
                    autor_id=connected.id,
                    texto="Conexión anterior",
                    fecha=base_date + timedelta(hours=9),
                ),
                Publicacion(
                    id=213,
                    autor_id=followed.id,
                    texto="Seguido reciente",
                    fecha=base_date + timedelta(hours=8),
                ),
                Publicacion(
                    id=214,
                    autor_id=followed.id,
                    texto="Seguido anterior",
                    fecha=base_date + timedelta(hours=7),
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

    def feed(
        self,
        limit: int,
        offset: int,
        social_author_ids: set[int] | None = None,
        seed: int = 123,
    ) -> list[Publicacion]:
        return self.repository.get_feed(
            social_author_ids={2, 3}
            if social_author_ids is None
            else social_author_ids,
            seed=seed,
            limit=limit,
            offset=offset,
        )

    def ids(
        self,
        limit: int,
        offset: int,
        social_author_ids: set[int] | None = None,
        seed: int = 123,
    ) -> list[int]:
        return [
            publication.id
            for publication in self.feed(
                limit,
                offset,
                social_author_ids,
                seed,
            )
        ]

    def test_feed_keeps_only_the_two_most_recent_posts_per_author(self):
        publications = self.feed(limit=50, offset=0)
        counts_by_author: dict[int, int] = {}
        for publication in publications:
            counts_by_author[publication.autor_id] = (
                counts_by_author.get(publication.autor_id, 0) + 1
            )

        self.assertLessEqual(max(counts_by_author.values()), 2)
        self.assertIn(201, [publication.id for publication in publications])
        self.assertIn(202, [publication.id for publication in publications])
        self.assertNotIn(203, [publication.id for publication in publications])

    def test_social_posts_are_stably_mixed_ahead_of_their_chronological_position(self):
        first_order = self.ids(limit=50, offset=0, seed=321)
        repeated_order = self.ids(limit=50, offset=0, seed=321)
        social_positions = [
            first_order.index(publication_id)
            for publication_id in (211, 212, 213, 214)
        ]

        self.assertEqual(first_order, repeated_order)
        self.assertLess(min(social_positions), 8)
        self.assertGreaterEqual(
            len({211, 212, 213, 214}.intersection(first_order[:10])),
            1,
        )

    def test_seed_changes_social_positions_without_changing_candidates(self):
        first_order = self.ids(limit=50, offset=0, seed=100)
        second_order = self.ids(limit=50, offset=0, seed=107)

        self.assertEqual(set(first_order), set(second_order))
        self.assertNotEqual(first_order, second_order)

    def test_pages_match_the_global_order_without_duplicates(self):
        complete_feed = self.ids(limit=50, offset=0)
        pages = [
            self.ids(limit=5, offset=offset)
            for offset in range(0, len(complete_feed), 5)
        ]
        paginated_feed = [publication_id for page in pages for publication_id in page]

        self.assertEqual(paginated_feed, complete_feed)
        self.assertEqual(len(set(paginated_feed)), len(paginated_feed))
        self.assertTrue(all(len(page) == 5 for page in pages[:-1]))

    def test_feed_without_social_candidates_fills_the_page_chronologically(self):
        first_page = self.ids(
            limit=10,
            offset=0,
            social_author_ids=set(),
        )

        self.assertEqual(len(first_page), 10)
        self.assertEqual(first_page[:2], [201, 202])
        self.assertNotIn(203, first_page)

    def test_empty_feed_returns_an_empty_list(self):
        self.db.query(Publicacion).delete()
        self.db.commit()

        self.assertEqual(self.ids(limit=20, offset=0), [])


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "La prueba del ranking del feed requiere la PostgreSQL configurada.",
)
class GlobalFeedPostgresTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        suffix = uuid4().hex
        authors = [
            Usuario(
                email=f"feed-author-{index}-{suffix}@example.com",
                nombre=f"Autor {index}",
                password_hash="not-used",
                headline="Prueba PostgreSQL del feed",
                ciudad="Buenos Aires",
            )
            for index in range(3)
        ]
        self.db.add_all(authors)
        self.db.flush()
        self.frequent_author_id = authors[0].id
        base_date = datetime(2026, 1, 2, 8, 0, 0)
        self.db.add_all(
            [
                Publicacion(
                    autor_id=authors[0].id,
                    texto=f"Frecuente {index}",
                    fecha=base_date + timedelta(minutes=index),
                )
                for index in range(3)
            ]
            + [
                Publicacion(
                    autor_id=authors[1].id,
                    texto="Social",
                    fecha=base_date - timedelta(hours=1),
                ),
                Publicacion(
                    autor_id=authors[2].id,
                    texto="General",
                    fecha=base_date + timedelta(hours=1),
                ),
            ]
        )
        self.db.flush()
        self.social_author_id = authors[1].id
        self.repository = PublicacionRepository(self.db)

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def test_postgresql_applies_author_limit_stable_order_and_pagination(self):
        complete_feed = self.repository.get_feed(
            social_author_ids={self.social_author_id},
            seed=456,
            limit=20,
            offset=0,
        )
        author_posts = [
            publication
            for publication in complete_feed
            if publication.autor_id == self.frequent_author_id
        ]
        first_page = self.repository.get_feed(
            social_author_ids={self.social_author_id},
            seed=456,
            limit=2,
            offset=0,
        )
        second_page = self.repository.get_feed(
            social_author_ids={self.social_author_id},
            seed=456,
            limit=2,
            offset=2,
        )

        self.assertEqual(len(author_posts), 2)
        self.assertEqual(
            [publication.id for publication in first_page + second_page],
            [publication.id for publication in complete_feed[:4]],
        )


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

    def test_feed_combines_followed_and_connected_authors_without_duplicates(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.seguimiento_repository = Mock()
        service.seguimiento_repository.get_followed_ids.return_value = {2, 3}
        service.conexion_repository = Mock()
        service.conexion_repository.get_accepted_by_user.return_value = [
            SimpleNamespace(usuario_a=1, usuario_b=3),
            SimpleNamespace(usuario_a=4, usuario_b=1),
        ]
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_feed.return_value = [
            post(20, 4, 10),
            post(21, 2, 9),
        ]

        result = service.get_feed(1, page=1, page_size=2)

        self.assertEqual([item.id for item in result], [20, 21])
        service.publicacion_repository.get_feed.assert_called_once_with(
            social_author_ids={2, 3, 4},
            seed=ANY,
            limit=2,
            offset=0,
        )

    def test_feed_second_page_translates_to_database_offset(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.seguimiento_repository = Mock()
        service.seguimiento_repository.get_followed_ids.return_value = set()
        service.conexion_repository = Mock()
        service.conexion_repository.get_accepted_by_user.return_value = []
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_feed.return_value = [
            post(30, 4, 8),
            post(31, 2, 7),
        ]

        result = service.get_feed(1, page=2, page_size=2)

        self.assertEqual([item.id for item in result], [30, 31])
        service.publicacion_repository.get_feed.assert_called_once_with(
            social_author_ids=set(),
            seed=ANY,
            limit=2,
            offset=2,
        )

    def test_feed_empty_page_still_uses_requested_page_size(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.seguimiento_repository = Mock()
        service.seguimiento_repository.get_followed_ids.return_value = set()
        service.conexion_repository = Mock()
        service.conexion_repository.get_accepted_by_user.return_value = []
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_feed.return_value = []

        result = service.get_feed(1, page=3, page_size=7)

        self.assertEqual(result, [])
        service.publicacion_repository.get_feed.assert_called_once_with(
            social_author_ids=set(),
            seed=ANY,
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
