import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.app import app
from src.db.connection import get_db
from src.dtos.conexiones_dto import ResumenRedResponseDTO
from src.mappers.conexion_mapper import ConexionMapper
from src.middlewares.auth_middleware import get_current_user
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
        existing = SimpleNamespace(seguidor_id=1, seguido_id=2, fecha=datetime.now())
        service.repository = Mock()
        service.repository.get.return_value = existing

        result = service.follow(1, 2)
        service.repository.create.assert_not_called()
        self.assertEqual(result.seguido_id, 2)
        service.unfollow(1, 2)
        service.repository.delete.assert_called_once_with(existing)

    def test_cannot_follow_self(self):
        service = SeguimientoService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.repository = Mock()

        with self.assertRaises(ConflictError):
            service.follow(1, 1)

    def test_first_page_places_up_to_five_followed_posts_before_general_posts(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.seguimiento_repository = Mock()
        service.seguimiento_repository.get_followed_ids.return_value = {2, 3}
        service.publicacion_repository = Mock()
        priority = [post(i, 2 if i % 2 else 3, 10 - i) for i in range(1, 6)]
        general = [post(20, 4, 1), post(21, 5, 0)]
        service.publicacion_repository.get_recent_by_authors.return_value = priority
        service.publicacion_repository.get_general.return_value = general

        result = service.get_feed(1, page=1, page_size=7)

        self.assertEqual([item.id for item in result], [1, 2, 3, 4, 5, 20, 21])
        service.publicacion_repository.get_general.assert_called_once_with(
            {1, 2, 3, 4, 5}, 1, 2, 0
        )

    def test_feed_pagination_skips_priorities_and_never_requeries_them(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.seguimiento_repository = Mock()
        service.seguimiento_repository.get_followed_ids.return_value = {2}
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_recent_by_authors.return_value = [post(10, 2, 10), post(11, 2, 9)]
        service.publicacion_repository.get_general.return_value = [post(30, 4, 8), post(31, 4, 7)]

        result = service.get_feed(1, page=2, page_size=2)

        self.assertEqual([item.id for item in result], [30, 31])
        service.publicacion_repository.get_general.assert_called_once_with({10, 11}, 1, 2, 0)

    def test_feed_without_following_uses_general_feed_and_honors_limit(self):
        service = FeedService(Mock())
        service.usuario_repository = Mock()
        service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=1)
        service.seguimiento_repository = Mock()
        service.seguimiento_repository.get_followed_ids.return_value = set()
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_recent_by_authors.return_value = []
        service.publicacion_repository.get_general.return_value = [post(50, 4, 1)]

        result = service.get_feed(1, page=1, page_size=1)

        self.assertEqual([item.id for item in result], [50])
        service.publicacion_repository.get_general.assert_called_once_with(set(), 1, 1, 0)


if __name__ == "__main__":
    unittest.main()
