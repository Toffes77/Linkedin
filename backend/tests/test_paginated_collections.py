import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.comentario_model import Comentario
from src.db.models.empresa_model import Empresa
from src.db.models.empresa_usuario_model import EmpresaUsuario, RolEmpresa
from src.db.models.oferta_model import Oferta
from src.db.models.postulacion_model import Postulacion
from src.db.models.promocion_model import Promocion
from src.db.models.publicacion_model import Publicacion
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user
from src.services.comentario_service import ComentarioService
from src.services.oferta_service import OfertaService
from src.services.postulacion_service import PostulacionService
from src.services.promocion_service import PromocionService
from src.services.usuario_service import UsuarioService
from src.utils.errors import BadRequestError, ForbiddenError


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Las pruebas de paginación requieren PostgreSQL.",
)
class PaginatedCollectionsPostgresTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        self.marker = uuid4().hex[:10]
        self.now = datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc)

        self.owner = self._user("Owner")
        self.recruiter = self._user("Recruiter")
        self.collaborator = self._user("Collaborator")
        self.applicants = [self._user(f"Paged Person {index}") for index in range(6)]
        self.company = Empresa(nombre=f"Paged Company {self.marker}")
        self.db.add(self.company)
        self.db.flush()
        self.db.add_all([
            EmpresaUsuario(empresa_id=self.company.id, usuario_id=self.owner.id, rol=RolEmpresa.OWNER),
            EmpresaUsuario(empresa_id=self.company.id, usuario_id=self.recruiter.id, rol=RolEmpresa.RECRUITER),
            EmpresaUsuario(empresa_id=self.company.id, usuario_id=self.collaborator.id, rol=RolEmpresa.COLLABORATOR),
        ])
        self.db.flush()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def _user(self, label: str) -> Usuario:
        user = Usuario(
            email=f"{label.lower().replace(' ', '-')}-{self.marker}@example.com",
            nombre=f"{label} {self.marker}",
            password_hash="hash",
            headline=f"Pagination {self.marker}",
            ciudad="Buenos Aires",
        )
        self.db.add(user)
        self.db.flush()
        return user

    def _collect(self, first_page, next_page):
        pages = [first_page]
        while pages[-1].has_more:
            pages.append(next_page(pages[-1].next_cursor))
        return pages, [item for page in pages for item in page.items]

    def test_comments_are_flat_lazy_limited_and_stable_at_any_depth(self):
        post = Publicacion(autor_id=self.owner.id, texto=f"Post {self.marker}", fecha=self.now)
        self.db.add(post)
        self.db.flush()
        roots = [Comentario(publicacion_id=post.id, usuario_id=self.owner.id, contenido=f"Root {index}", fecha=self.now) for index in range(6)]
        self.db.add_all(roots)
        self.db.flush()
        replies = [Comentario(publicacion_id=post.id, usuario_id=self.owner.id, contenido=f"Reply {index}", fecha=self.now, comentario_padre_id=roots[0].id) for index in range(5)]
        self.db.add_all(replies)
        self.db.flush()
        parent = replies[0]
        for depth in range(80):
            parent = Comentario(publicacion_id=post.id, usuario_id=self.owner.id, contenido=f"Depth {depth}", fecha=self.now, comentario_padre_id=parent.id)
            self.db.add(parent)
            self.db.flush()

        statements: list[str] = []
        def capture(_conn, _cursor, statement, _parameters, _context, _many):
            if "comentario" in statement.lower(): statements.append(statement)
        event.listen(self.connection, "before_cursor_execute", capture)
        try:
            service = ComentarioService(self.db)
            first = service.list_roots(post.id, cursor=None, limit=2)
            pages, items = self._collect(first, lambda cursor: service.list_roots(post.id, cursor=cursor, limit=2))
            reply_first = service.list_replies(roots[0].id, cursor=None, limit=2)
            reply_pages, reply_items = self._collect(reply_first, lambda cursor: service.list_replies(roots[0].id, cursor=cursor, limit=2))
        finally:
            event.remove(self.connection, "before_cursor_execute", capture)

        self.assertEqual(len(items), 6)
        self.assertEqual([item.id for item in items], sorted((root.id for root in roots), reverse=True))
        self.assertEqual(len({item.id for item in items}), 6)
        self.assertTrue(all(len(page.items) <= 2 for page in pages))
        self.assertNotIn("respuestas", items[0].model_dump())
        self.assertEqual(next(item for item in items if item.id == roots[0].id).cantidad_respuestas, 5)
        self.assertEqual([item.id for item in reply_items], sorted(reply.id for reply in replies))
        self.assertTrue(all(len(page.items) <= 2 for page in reply_pages))
        self.assertNotIn(parent.id, {item.id for item in reply_items})
        self.assertTrue(any("LIMIT" in statement.upper() for statement in statements))

    def test_profiles_offers_applications_and_promotions_use_stable_keyset_pages(self):
        user_service = UsuarioService(self.db)
        first_users = user_service.search(f"Paged Person", cursor=None, limit=2)
        user_pages, users = self._collect(first_users, lambda cursor: user_service.search("Paged Person", cursor=cursor, limit=2))
        self.assertEqual(len(users), 6)
        self.assertEqual(len({user.id for user in users}), 6)
        self.assertTrue(all(len(page.items) <= 2 for page in user_pages))
        self.assertEqual([user.nombre.lower() for user in users], sorted(user.nombre.lower() for user in users))
        with self.assertRaises(BadRequestError):
            user_service.search("different filter", cursor=first_users.next_cursor, limit=2)

        offers = [Oferta(empresa_id=self.company.id, titulo=f"Offer {index} {self.marker}", descripcion="Description", publicada=True, fecha_publicacion=self.now) for index in range(6)]
        draft = Oferta(empresa_id=self.company.id, titulo=f"Draft {self.marker}", descripcion="Description", publicada=False)
        self.db.add_all([*offers, draft])
        self.db.flush()
        offer_service = OfertaService(self.db)
        public_pages, public_items = self._collect(offer_service.get_publicadas(self.marker, limit=2), lambda cursor: offer_service.get_publicadas(self.marker, cursor=cursor, limit=2))
        self.assertEqual([item.id for item in public_items], sorted((offer.id for offer in offers), reverse=True))
        self.assertNotIn(draft.id, {item.id for item in public_items})
        manager_page = offer_service.get_by_empresa(self.company.id, self.owner.id, limit=20)
        collaborator_page = offer_service.get_by_empresa(self.company.id, self.collaborator.id, limit=20)
        self.assertIn(draft.id, {item.id for item in manager_page.items})
        self.assertNotIn(draft.id, {item.id for item in collaborator_page.items})
        self.assertTrue(all(len(page.items) <= 2 for page in public_pages))

        applications = [Postulacion(oferta_id=offers[0].id, usuario_id=user.id, fecha=self.now) for user in self.applicants]
        self.db.add_all(applications)
        self.db.flush()
        application_service = PostulacionService(self.db)
        first_applications = application_service.get_by_oferta(offers[0].id, self.owner.id, limit=2)
        application_pages, application_items = self._collect(first_applications, lambda cursor: application_service.get_by_oferta(offers[0].id, self.recruiter.id, cursor=cursor, limit=2))
        self.assertEqual([item.id for item in application_items], sorted((item.id for item in applications), reverse=True))
        self.assertTrue(all(len(page.items) <= 2 for page in application_pages))
        with self.assertRaises(ForbiddenError):
            application_service.get_by_oferta(offers[0].id, self.collaborator.id, limit=2)
        own = application_service.get_by_usuario(self.applicants[0].id, self.applicants[0].id, oferta_id=offers[0].id, limit=1)
        self.assertEqual([item.usuario_id for item in own.items], [self.applicants[0].id])

        promotions = [Promocion(usuario_id=self.applicants[0].id, titulo=f"Promotion {index}", descripcion="Description", fecha_creacion=self.now) for index in range(5)]
        self.db.add_all(promotions)
        self.db.flush()
        promotion_service = PromocionService(self.db)
        promotion_pages, promotion_items = self._collect(promotion_service.get_mine(self.applicants[0].id, limit=2), lambda cursor: promotion_service.get_mine(self.applicants[0].id, cursor=cursor, limit=2))
        self.assertEqual([item.id for item in promotion_items], sorted((item.id for item in promotions), reverse=True))
        self.assertTrue(all(len(page.items) <= 2 for page in promotion_pages))

    def test_limits_invalid_cursors_and_indexes_are_controlled(self):
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.owner.id)
        client = TestClient(app)
        for path in (
            "/api/publicaciones/1/comentarios?limit=51",
            "/api/buscar/usuarios?q=Paged&limit=51",
            "/api/ofertas/publicadas?limit=51",
            f"/api/empresas/{self.company.id}/ofertas?limit=51",
            "/api/ofertas/1/postulaciones?limit=51",
            f"/api/usuarios/{self.owner.id}/postulaciones?limit=51",
            "/api/promociones/mias?limit=51",
        ):
            with self.subTest(path=path): self.assertEqual(client.get(path).status_code, 422)

        self.assertEqual(client.get("/api/buscar/usuarios", params={"q": "Paged", "cursor": "invalid"}).status_code, 400)
        index_names = {table: {item["name"] for item in inspect(engine).get_indexes(table)} for table in ("usuario", "comentario", "oferta", "postulacion", "promocion")}
        self.assertIn("idx_usuario_nombre_id", index_names["usuario"])
        self.assertIn("idx_comentario_raiz_publicacion_fecha", index_names["comentario"])
        self.assertIn("idx_oferta_publicada_fecha_id", index_names["oferta"])
        self.assertIn("idx_oferta_empresa_id", index_names["oferta"])
        self.assertIn("idx_postulacion_usuario_fecha_id", index_names["postulacion"])
        self.assertIn("idx_postulacion_oferta_fecha_id", index_names["postulacion"])
        self.assertIn("idx_promocion_usuario_fecha", index_names["promocion"])


if __name__ == "__main__":
    unittest.main()
