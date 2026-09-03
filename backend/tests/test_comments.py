import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, get_db
from src.db.models.comentario_model import Comentario
from src.db.models.publicacion_model import Publicacion
from src.db.models.usuario_model import Usuario
from src.dtos.comentario_dto import (
    AutorComentarioDTO,
    ComentarioResponseDTO,
    CrearComentarioDTO,
)
from src.middlewares.auth_middleware import get_current_user
from src.mappers.comentario_mapper import ComentarioMapper
from src.repositories.comentario_repository import ComentarioRepository
from src.services.comentario_service import ComentarioService
from src.utils.errors import BadRequestError, ForbiddenError, NotFoundError


def user(user_id: int, name: str = "Usuario"):
    return SimpleNamespace(
        id=user_id,
        nombre=name,
        headline=f"{name} headline",
        foto_perfil_url=None,
    )


def comment(
    comment_id: int,
    *,
    user_id: int = 7,
    parent_id: int | None = None,
    responses: list | None = None,
    content: str = "Comentario",
):
    return SimpleNamespace(
        id=comment_id,
        publicacion_id=3,
        usuario_id=user_id,
        contenido=content,
        fecha=datetime(2026, 8, 24, 12, comment_id % 60),
        comentario_padre_id=parent_id,
        autor=user(user_id, f"Usuario {user_id}"),
        respuestas=responses or [],
    )


class CommentServiceTests(unittest.TestCase):
    def service(self) -> ComentarioService:
        service = ComentarioService(Mock())
        service.repository = Mock()
        service.publicacion_repository = Mock()
        service.publicacion_repository.get_by_id.return_value = SimpleNamespace(id=3)
        return service

    def test_create_trims_content_and_uses_authenticated_user_as_author(self):
        service = self.service()
        service.repository.create.side_effect = lambda data: comment(
            10,
            user_id=data.usuario_id,
            content=data.contenido,
        )

        result = service.create(3, CrearComentarioDTO(contenido="  Muy bueno  "), 7)

        created = service.repository.create.call_args.args[0]
        self.assertEqual(created.usuario_id, 7)
        self.assertEqual(created.publicacion_id, 3)
        self.assertEqual(created.contenido, "Muy bueno")
        self.assertIsNone(created.comentario_padre_id)
        self.assertEqual(result.autor.id, 7)

    def test_empty_comment_is_rejected(self):
        service = self.service()

        with self.assertRaises(BadRequestError):
            service.create(3, CrearComentarioDTO(contenido="   "), 7)

        service.repository.create.assert_not_called()

    def test_reply_is_attached_to_main_comment(self):
        service = self.service()
        root = comment(11)
        service.repository.get_by_id.return_value = root
        service.repository.create.side_effect = lambda data: comment(
            12,
            user_id=data.usuario_id,
            parent_id=data.comentario_padre_id,
            content=data.contenido,
        )

        result = service.reply(11, CrearComentarioDTO(contenido=" De acuerdo "), 8)

        created = service.repository.create.call_args.args[0]
        self.assertEqual(created.comentario_padre_id, 11)
        self.assertEqual(created.usuario_id, 8)
        self.assertEqual(result.comentario_padre_id, 11)

    def test_reply_to_a_reply_keeps_its_immediate_parent(self):
        service = self.service()
        reply = comment(12, parent_id=11)
        service.repository.get_by_id.return_value = reply
        service.repository.create.side_effect = lambda data: comment(
            13,
            user_id=data.usuario_id,
            parent_id=data.comentario_padre_id,
        )

        service.reply(12, CrearComentarioDTO(contenido="También"), 9)

        created = service.repository.create.call_args.args[0]
        self.assertEqual(created.comentario_padre_id, 12)
        service.repository.get_by_id.assert_called_once_with(12)

    def test_reply_to_missing_comment_is_rejected(self):
        service = self.service()
        service.repository.get_by_id.return_value = None

        with self.assertRaises(NotFoundError):
            service.reply(999, CrearComentarioDTO(contenido="Respuesta"), 7)

        service.repository.create.assert_not_called()

    def test_list_returns_only_a_bounded_page_of_roots(self):
        service = self.service()
        root = comment(11)
        service.repository.get_roots_page.return_value = [(root, 4)]

        result = service.list_roots(3, cursor=None, limit=10)

        self.assertEqual([item.id for item in result.items], [11])
        self.assertEqual(result.items[0].cantidad_respuestas, 4)
        service.repository.get_roots_page.assert_called_once_with(
            3,
            limit=11,
            after=None,
        )

    def test_own_comment_can_be_deleted(self):
        service = self.service()
        own_comment = comment(11, user_id=7)
        service.repository.get_by_id.return_value = own_comment

        service.delete(11, usuario_id=7)

        service.repository.delete.assert_called_once_with(own_comment)

    def test_foreign_comment_cannot_be_deleted(self):
        service = self.service()
        service.repository.get_by_id.return_value = comment(11, user_id=8)

        with self.assertRaises(ForbiddenError):
            service.delete(11, usuario_id=7)

        service.repository.delete.assert_not_called()

    def test_counter_includes_main_comments_and_responses(self):
        service = self.service()
        service.repository.count_by_publicacion.return_value = 8

        result = service.count_by_publicacion(3)

        self.assertEqual(result.cantidad, 8)
        service.repository.count_by_publicacion.assert_called_once_with(3)


class CommentRouterTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: Mock()
        app.dependency_overrides[get_current_user] = lambda: user(7)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_create_endpoint_uses_authenticated_user_and_rejects_user_id(self):
        created = ComentarioResponseDTO(
            id=10,
            publicacion_id=3,
            usuario_id=7,
            contenido="Hola",
            fecha=datetime(2026, 8, 24, 12, 0),
            autor=AutorComentarioDTO(
                id=7,
                nombre="Usuario 7",
                headline="Headline",
            ),
        )
        with patch(
            "src.routers.comentario_router.ComentarioService.create",
            return_value=created,
        ) as create:
            response = TestClient(app).post(
                "/api/publicaciones/3/comentarios",
                json={"contenido": "Hola"},
            )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(create.call_args.args[2], 7)
        forbidden_payload = TestClient(app).post(
            "/api/publicaciones/3/comentarios",
            json={"contenido": "Hola", "usuario_id": 999},
        )
        self.assertEqual(forbidden_payload.status_code, 422)

    def test_comment_endpoints_require_authentication(self):
        app.dependency_overrides.pop(get_current_user)

        response = TestClient(app).get("/api/publicaciones/3/comentarios")

        self.assertEqual(response.status_code, 401)


class CommentPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(cls.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.author = Usuario(
            email="comments-author@example.com",
            nombre="Autor",
            password_hash="hash",
            headline="Backend Developer",
            ciudad="Buenos Aires",
        )
        self.reader = Usuario(
            email="comments-reader@example.com",
            nombre="Lector",
            password_hash="hash",
            headline="Frontend Developer",
            ciudad="Rosario",
        )
        self.db.add_all([self.author, self.reader])
        self.db.flush()
        self.post = Publicacion(autor_id=self.author.id, texto="Publicación")
        self.db.add(self.post)
        self.db.flush()
        now = datetime(2026, 8, 24, 12, 0)
        old_root = Comentario(
            publicacion_id=self.post.id,
            usuario_id=self.author.id,
            contenido="Primero",
            fecha=now,
        )
        new_root = Comentario(
            publicacion_id=self.post.id,
            usuario_id=self.reader.id,
            contenido="Segundo",
            fecha=now + timedelta(minutes=3),
        )
        self.db.add_all([old_root, new_root])
        self.db.flush()
        old_reply = Comentario(
            publicacion_id=self.post.id,
            usuario_id=self.reader.id,
            contenido="Respuesta antigua",
            fecha=now + timedelta(minutes=1),
            comentario_padre_id=old_root.id,
        )
        new_reply = Comentario(
            publicacion_id=self.post.id,
            usuario_id=self.author.id,
            contenido="Respuesta nueva",
            fecha=now + timedelta(minutes=2),
            comentario_padre_id=old_root.id,
        )
        self.db.add_all([old_reply, new_reply])
        self.db.flush()
        self.db.add(
            Comentario(
                publicacion_id=self.post.id,
                usuario_id=self.author.id,
                contenido="Respuesta anidada",
                fecha=now + timedelta(minutes=2),
                comentario_padre_id=old_reply.id,
            )
        )
        self.db.commit()
        self.old_root_id = old_root.id

    def tearDown(self):
        self.db.rollback()
        self.db.query(Comentario).delete()
        self.db.query(Publicacion).delete()
        self.db.query(Usuario).delete()
        self.db.commit()
        self.db.close()

    def test_listing_order_count_and_cascade_are_persisted(self):
        repository = ComentarioRepository(self.db)

        roots = repository.get_roots_page(self.post.id, limit=10)

        self.assertEqual([item.contenido for item, _ in roots], ["Segundo", "Primero"])
        self.assertEqual(
            [item.contenido for item, _ in repository.get_direct_replies_page(self.old_root_id, limit=10)],
            ["Respuesta antigua", "Respuesta nueva"],
        )
        self.assertEqual(roots[1][1], 2)
        self.assertEqual(repository.count_by_publicacion(self.post.id), 5)

        repository.delete(repository.get_by_id(self.old_root_id))

        self.assertEqual(repository.count_by_publicacion(self.post.id), 1)


if __name__ == "__main__":
    unittest.main()
