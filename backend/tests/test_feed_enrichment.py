import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.comentario_model import Comentario
from src.db.models.empresa_model import Empresa
from src.db.models.publicacion_model import Publicacion
from src.db.models.reaciones_model import Reacciones
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user
from src.repositories.publicacion_repository import PublicacionRepository
from src.services.publicacion_service import PublicacionService


class FeedEnrichmentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        suffix = uuid4().hex
        self.viewer = self._user(f"viewer-{suffix}@example.com", "Viewer")
        self.author = self._user(f"author-{suffix}@example.com", "Author")
        self.other = self._user(f"other-{suffix}@example.com", "Other")
        self.db.add_all([self.viewer, self.author, self.other])
        self.db.flush()
        self.posts = [
            Publicacion(autor_id=self.author.id, texto=f"Publicación {index}")
            for index in range(20)
        ]
        self.db.add_all(self.posts)
        self.companies = [
            Empresa(nombre=f"Empresa {suffix} A"),
            Empresa(nombre=f"Empresa {suffix} B"),
        ]
        self.db.add_all(self.companies)
        self.db.flush()
        self.db.add_all(
            [
                Reacciones(
                    usuario_id=self.viewer.id,
                    publicacion_id=self.posts[-1].id,
                    tipo="like",
                ),
                Reacciones(
                    usuario_id=self.other.id,
                    publicacion_id=self.posts[-1].id,
                    tipo="celebrar",
                ),
                Comentario(
                    publicacion_id=self.posts[-1].id,
                    usuario_id=self.viewer.id,
                    contenido="Primero",
                ),
                Comentario(
                    publicacion_id=self.posts[-1].id,
                    usuario_id=self.other.id,
                    contenido="Segundo",
                ),
            ]
        )
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.viewer
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def _user(email: str, name: str) -> Usuario:
        return Usuario(
            email=email,
            nombre=name,
            password_hash="not-used",
            headline=f"Headline {name}",
            ciudad="Buenos Aires",
        )

    def _capture_selects(self, action):
        statements: list[str] = []

        def capture(_conn, _cursor, statement, _parameters, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(" ".join(statement.split()))

        event.listen(self.connection, "before_cursor_execute", capture)
        try:
            result = action()
        finally:
            event.remove(self.connection, "before_cursor_execute", capture)
        return result, statements

    def test_publication_pages_are_enriched_with_two_batch_aggregations(self):
        self.db.expire_all()
        service = PublicacionService(self.db)
        cards, statements = self._capture_selects(
            lambda: service.get_by_autor(
                self.author.id,
                limit=20,
                usuario_actual_id=self.viewer.id,
            )
        )

        target = next(card for card in cards if card.id == self.posts[-1].id)
        self.assertEqual(target.autor.nombre, self.author.nombre)
        self.assertEqual(
            target.reacciones,
            {"like": 1, "celebrar": 1, "apoyar": 0, "interesante": 0},
        )
        self.assertEqual(target.mi_reaccion, "like")
        self.assertEqual(target.cantidad_comentarios, 2)

        reaction_queries = [
            statement
            for statement in statements
            if "FROM reacciones" in statement
        ]
        comment_queries = [
            statement
            for statement in statements
            if "FROM comentario" in statement
        ]
        self.assertEqual(len(reaction_queries), 1)
        self.assertIn("GROUP BY", reaction_queries[0].upper())
        self.assertEqual(len(comment_queries), 1)
        self.assertIn("GROUP BY", comment_queries[0].upper())

    def test_query_count_does_not_grow_with_publication_count(self):
        service = PublicacionService(self.db)
        self.db.expire_all()
        _, five_statements = self._capture_selects(
            lambda: service.get_by_autor(
                self.author.id,
                limit=5,
                usuario_actual_id=self.viewer.id,
            )
        )
        self.db.expire_all()
        _, twenty_statements = self._capture_selects(
            lambda: service.get_by_autor(
                self.author.id,
                limit=20,
                usuario_actual_id=self.viewer.id,
            )
        )

        self.assertEqual(len(five_statements), len(twenty_statements))
        self.assertLessEqual(len(twenty_statements), 6)

    def test_feed_query_count_is_bounded_by_page_not_by_card(self):
        suffix = uuid4().hex
        extra_authors = [
            self._user(f"feed-{index}-{suffix}@example.com", f"Feed {index}")
            for index in range(18)
        ]
        self.db.add_all(extra_authors)
        self.db.flush()
        self.db.add_all(
            [
                Publicacion(autor_id=author.id, texto=f"Post de {author.nombre}")
                for author in extra_authors
            ]
        )
        self.db.commit()

        with patch.object(
            PublicacionRepository,
            "get_visibility_snapshot",
            return_value=None,
        ):
            self.db.expire_all()
            small, small_statements = self._capture_selects(
                lambda: self.client.get("/api/feed", params={"page_size": 5})
            )
            self.db.expire_all()
            large, large_statements = self._capture_selects(
                lambda: self.client.get("/api/feed", params={"page_size": 20})
            )

        self.assertEqual(small.status_code, 200, small.text)
        self.assertEqual(large.status_code, 200, large.text)
        self.assertEqual(len(small.json()["items"]), 5)
        self.assertEqual(len(large.json()["items"]), 20)
        self.assertEqual(len(small_statements), len(large_statements))
        self.assertEqual(
            sum("FROM reacciones" in statement for statement in large_statements),
            1,
        )
        self.assertEqual(
            sum("FROM comentario" in statement for statement in large_statements),
            1,
        )

    def test_feed_contract_contains_author_counts_and_current_reaction(self):
        with patch.object(
            PublicacionRepository,
            "get_visibility_snapshot",
            return_value=None,
        ):
            response = self.client.get("/api/feed", params={"page_size": 10})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["items"])
        for item in response.json()["items"]:
            self.assertIn("autor", item)
            self.assertIn("reacciones", item)
            self.assertIn("mi_reaccion", item)
            self.assertIn("cantidad_comentarios", item)
        target = next(
            item
            for item in response.json()["items"]
            if item["id"] == self.posts[-1].id
        )
        self.assertEqual(target["autor"]["id"], self.author.id)
        self.assertEqual(target["reacciones"]["like"], 1)
        self.assertEqual(target["mi_reaccion"], "like")
        self.assertEqual(target["cantidad_comentarios"], 2)

    def test_company_batch_deduplicates_and_executes_one_select(self):
        missing_id = max(company.id for company in self.companies) + 100_000
        response, statements = self._capture_selects(
            lambda: self.client.get(
                "/api/empresas/batch",
                params=[
                    ("ids", self.companies[0].id),
                    ("ids", self.companies[0].id),
                    ("ids", self.companies[1].id),
                    ("ids", missing_id),
                ],
            )
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            [company["id"] for company in response.json()],
            [self.companies[0].id, self.companies[1].id],
        )
        company_selects = [
            statement
            for statement in statements
            if "FROM empresa" in statement and "empresa_usuario" not in statement
        ]
        self.assertEqual(len(company_selects), 1)

        excessive = self.client.get(
            "/api/empresas/batch",
            params=[("ids", index + 1) for index in range(51)],
        )
        self.assertEqual(excessive.status_code, 422, excessive.text)

    def test_public_reaction_counts_use_one_grouped_query_and_fill_zeros(self):
        response, statements = self._capture_selects(
            lambda: self.client.get(
                f"/api/publicaciones/{self.posts[-1].id}/reacciones"
            )
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"like": 1, "celebrar": 1, "apoyar": 0, "interesante": 0},
        )
        reaction_queries = [
            statement
            for statement in statements
            if "FROM reacciones" in statement
        ]
        self.assertEqual(len(reaction_queries), 1)
        self.assertIn("GROUP BY", reaction_queries[0].upper())

    def test_reaction_batch_index_is_synchronized(self):
        model_indexes = {index.name for index in Reacciones.__table__.indexes}
        tables_sql = Path("src/db/tables.sql").read_text(encoding="utf-8")
        migration_sql = Path(
            "src/db/migrations/20260903_feed_enrichment_indexes.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("idx_reacciones_publicacion_tipo", model_indexes)
        self.assertIn("idx_reacciones_publicacion_tipo", tables_sql)
        self.assertIn("idx_reacciones_publicacion_tipo", migration_sql)


if __name__ == "__main__":
    unittest.main()
