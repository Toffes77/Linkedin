import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app import app
from src.db.connection import SessionLocal, engine
from src.db.models.publicacion_model import Publicacion
from src.db.models.reaciones_model import Reacciones
from src.db.models.usuario_model import Usuario
from src.dtos.auth_dto import LoginDTO
from src.dtos.usuario_dto import CreateUsuarioDTO
from src.services.auth_service import AuthService
from src.services.publicacion_service import PublicacionService
from src.services.usuario_service import UsuarioService
from src.utils.errors import ConflictError, ForbiddenError
from src.utils.hash import hash_password


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Estas regresiones requieren la PostgreSQL configurada.",
)
class PublicationReactionCascadeTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        suffix = uuid4().hex
        self.author = self._user(f"cascade-author-{suffix}@example.com", "Author")
        self.reactor = self._user(f"cascade-reactor-{suffix}@example.com", "Reactor")
        self.db.add_all([self.author, self.reactor])
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    @staticmethod
    def _user(email: str, name: str) -> Usuario:
        return Usuario(
            email=email,
            nombre=name,
            password_hash="not-used",
            headline="Cascade test",
            ciudad="Buenos Aires",
        )

    def _post_with_reaction(self) -> tuple[Publicacion, Reacciones]:
        post = Publicacion(autor_id=self.author.id, texto="Post with reaction")
        self.db.add(post)
        self.db.flush()
        reaction = Reacciones(
            usuario_id=self.reactor.id,
            publicacion_id=post.id,
            tipo="like",
        )
        self.db.add(reaction)
        self.db.commit()
        return post, reaction

    def test_author_can_delete_post_with_reaction_and_cascade_removes_reaction(self):
        post, reaction = self._post_with_reaction()
        post_id = post.id
        reaction_key = (reaction.usuario_id, reaction.publicacion_id)

        PublicacionService(self.db).delete(post_id, self.author.id)

        self.assertIsNone(self.db.get(Publicacion, post_id))
        self.assertIsNone(self.db.get(Reacciones, reaction_key))

    def test_database_cascade_applies_without_loading_orm_relationship(self):
        post, reaction = self._post_with_reaction()
        post_id = post.id
        reaction_key = (reaction.usuario_id, reaction.publicacion_id)
        self.db.expunge_all()

        self.db.execute(delete(Publicacion).where(Publicacion.id == post_id))
        self.db.commit()

        self.assertIsNone(self.db.get(Publicacion, post_id))
        self.assertIsNone(self.db.get(Reacciones, reaction_key))

    def test_foreign_user_still_cannot_delete_post_or_its_reaction(self):
        post, reaction = self._post_with_reaction()
        post_id = post.id
        reaction_key = (reaction.usuario_id, reaction.publicacion_id)

        with self.assertRaises(ForbiddenError):
            PublicacionService(self.db).delete(post_id, self.reactor.id)

        self.assertIsNotNone(self.db.get(Publicacion, post_id))
        self.assertIsNotNone(self.db.get(Reacciones, reaction_key))


@unittest.skipUnless(
    engine.dialect.name == "postgresql",
    "Estas regresiones requieren la PostgreSQL configurada.",
)
class CaseInsensitiveEmailTests(unittest.TestCase):
    def setUp(self):
        self.suffix = uuid4().hex
        self.email_fragment = f"email-integrity-{self.suffix}"

    def tearDown(self):
        with SessionLocal() as db:
            db.query(Usuario).filter(
                func.lower(Usuario.email).contains(self.email_fragment)
            ).delete(synchronize_session=False)
            db.commit()

    def _dto(self, email: str) -> CreateUsuarioDTO:
        return CreateUsuarioDTO(
            email=email,
            password="Password123",
            nombre="Email Integrity",
            headline="Case insensitive email",
            ciudad="Buenos Aires",
        )

    def test_registration_normalizes_email_and_case_variant_returns_409(self):
        original = f"Email-Integrity-{self.suffix}@Example.COM"
        variant = original.lower()

        with TestClient(app) as client:
            first = client.post("/api/usuarios", json=self._dto(original).model_dump(mode="json"))
            second = client.post("/api/usuarios", json=self._dto(variant).model_dump(mode="json"))

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 409, second.text)
        with SessionLocal() as db:
            stored = db.query(Usuario).filter(func.lower(Usuario.email) == variant).one()
            self.assertEqual(stored.email, variant)

    def test_login_lookup_is_case_insensitive(self):
        stored_email = f"email-integrity-{self.suffix}@example.com"
        with SessionLocal() as db:
            user = Usuario(
                email=stored_email,
                nombre="Login Email",
                password_hash=hash_password("Password123"),
                headline="Login",
                ciudad="Buenos Aires",
            )
            db.add(user)
            db.commit()

        with SessionLocal() as db:
            token = AuthService(db).login(
                LoginDTO(email=stored_email.upper(), password="Password123")
            )
            self.assertTrue(token.access_token)

    def test_database_unique_index_rejects_case_variant_directly(self):
        mixed = f"Email-Integrity-{self.suffix}@Example.com"
        lower = mixed.lower()
        with SessionLocal() as db:
            db.add(
                Usuario(
                    email=mixed,
                    nombre="Mixed",
                    password_hash="not-used",
                    headline="Mixed",
                    ciudad="Buenos Aires",
                )
            )
            db.commit()

            db.add(
                Usuario(
                    email=lower,
                    nombre="Lower",
                    password_hash="not-used",
                    headline="Lower",
                    ciudad="Buenos Aires",
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()

    def test_concurrent_case_variants_create_one_account_and_return_business_error(self):
        lower = f"email-integrity-{self.suffix}@example.com"
        upper = lower.upper()
        barrier = Barrier(2)

        def register(email: str) -> tuple[str, int]:
            with SessionLocal() as db:
                pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
                service = UsuarioService(db)
                original_lookup = service.repository.get_by_email

                def synchronized_lookup(candidate: str):
                    result = original_lookup(candidate)
                    barrier.wait(timeout=5)
                    return result

                service.repository.get_by_email = synchronized_lookup
                try:
                    service.create(self._dto(email))
                    return "ok", pid
                except ConflictError:
                    return "conflict", pid

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(register, (lower, upper)))

        self.assertEqual(sorted(result for result, _ in results), ["conflict", "ok"])
        self.assertEqual(len({pid for _, pid in results}), 2)
        with SessionLocal() as db:
            matching = db.query(Usuario).filter(func.lower(Usuario.email) == lower).all()
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0].email, lower)


if __name__ == "__main__":
    unittest.main()
