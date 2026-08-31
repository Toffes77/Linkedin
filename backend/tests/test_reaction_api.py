import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import engine, get_db
from src.db.models.publicacion_model import Publicacion
from src.db.models.reaciones_model import Reacciones
from src.db.models.usuario_model import Usuario
from src.middlewares.auth_middleware import get_current_user


class ReactionApiTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        suffix = uuid4().hex
        self.user = self._user(f"reaction-{suffix}@example.com", "Reactor")
        self.other_user = self._user(
            f"reaction-other-{suffix}@example.com",
            "Other reactor",
        )
        self.db.add_all([self.user, self.other_user])
        self.db.flush()
        self.post = Publicacion(autor_id=self.other_user.id, texto="Post para reaccionar")
        self.db.add(self.post)
        self.db.commit()

        self.current_user = self.user
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
    def _user(email: str, name: str) -> Usuario:
        return Usuario(
            email=email,
            nombre=name,
            password_hash="not-used",
            headline="Reacciones",
            ciudad="Buenos Aires",
        )

    def _react(self, reaction_type: str = "like"):
        return self.client.post(
            "/api/reacciones",
            json={"publicacion_id": self.post.id, "tipo": reaction_type},
        )

    def test_create_and_get_my_reaction_reconstructs_persisted_state(self):
        created = self._react("interesante")
        loaded = self.client.get(
            f"/api/publicaciones/{self.post.id}/reacciones/me"
        )

        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(loaded.json()["tipo"], "interesante")

    def test_changing_type_updates_the_single_existing_row(self):
        self._react("like")
        changed = self.client.patch(
            f"/api/publicaciones/{self.post.id}/reacciones",
            json={"tipo": "apoyar"},
        )

        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["tipo"], "apoyar")
        self.assertEqual(
            self.db.query(Reacciones).filter(
                Reacciones.usuario_id == self.user.id,
                Reacciones.publicacion_id == self.post.id,
            ).count(),
            1,
        )

    def test_counts_include_all_users_and_their_independent_reactions(self):
        self._react("like")
        self.current_user = self.other_user
        self._react("celebrar")

        counts = self.client.get(
            f"/api/publicaciones/{self.post.id}/reacciones"
        )
        own = self.client.get(
            f"/api/publicaciones/{self.post.id}/reacciones/me"
        )

        self.assertEqual(counts.status_code, 200, counts.text)
        self.assertEqual(counts.json()["like"], 1)
        self.assertEqual(counts.json()["celebrar"], 1)
        self.assertEqual(own.json()["tipo"], "celebrar")

    def test_delete_removes_only_current_users_reaction_and_is_idempotent(self):
        self._react("like")
        self.current_user = self.other_user
        self._react("apoyar")
        self.current_user = self.user

        first_delete = self.client.delete(
            f"/api/publicaciones/{self.post.id}/reacciones/me"
        )
        second_delete = self.client.delete(
            f"/api/publicaciones/{self.post.id}/reacciones/me"
        )
        own = self.client.get(
            f"/api/publicaciones/{self.post.id}/reacciones/me"
        )
        counts = self.client.get(
            f"/api/publicaciones/{self.post.id}/reacciones"
        )

        self.assertEqual(first_delete.status_code, 204, first_delete.text)
        self.assertEqual(second_delete.status_code, 204, second_delete.text)
        self.assertIsNone(own.json())
        self.assertEqual(counts.json()["like"], 0)
        self.assertEqual(counts.json()["apoyar"], 1)

    def test_unknown_publication_is_rejected_for_get_and_delete(self):
        missing_id = self.post.id + 1_000_000
        loaded = self.client.get(
            f"/api/publicaciones/{missing_id}/reacciones/me"
        )
        deleted = self.client.delete(
            f"/api/publicaciones/{missing_id}/reacciones/me"
        )
        self.assertEqual(loaded.status_code, 404, loaded.text)
        self.assertEqual(deleted.status_code, 404, deleted.text)

    def test_authenticated_endpoints_reject_anonymous_users_but_counts_stay_public(self):
        app.dependency_overrides.pop(get_current_user)
        try:
            own = self.client.get(
                f"/api/publicaciones/{self.post.id}/reacciones/me"
            )
            deleted = self.client.delete(
                f"/api/publicaciones/{self.post.id}/reacciones/me"
            )
            counts = self.client.get(
                f"/api/publicaciones/{self.post.id}/reacciones"
            )
        finally:
            app.dependency_overrides[get_current_user] = lambda: self.current_user

        self.assertEqual(own.status_code, 401, own.text)
        self.assertEqual(deleted.status_code, 401, deleted.text)
        self.assertEqual(counts.status_code, 200, counts.text)


if __name__ == "__main__":
    unittest.main()
