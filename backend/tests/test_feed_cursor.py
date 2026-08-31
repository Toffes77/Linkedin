import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app  # noqa: F401 - registra todos los modelos SQLAlchemy
from src.db.connection import Base, SessionLocal, engine as postgres_engine
from src.db.models.publicacion_model import Publicacion
from src.db.models.seguimiento_model import Seguimiento
from src.db.models.usuario_model import Usuario
from src.services.feed_service import FeedService
from src.utils.errors import BadRequestError
from src.utils.feed_cursor import decode_feed_cursor


class FeedCursorTests(unittest.TestCase):
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
        self.viewer = self._user(1, "cursor-viewer@example.com")
        self.authors = [
            self._user(index, f"cursor-author-{index}@example.com")
            for index in range(2, 9)
        ]
        self.late_author = self._user(9, "cursor-late@example.com")
        self.other_viewer = self._user(10, "cursor-other@example.com")
        self.db.add_all(
            [self.viewer, *self.authors, self.late_author, self.other_viewer]
        )
        self.db.flush()
        self.db.add(
            Seguimiento(
                seguidor_id=self.viewer.id,
                seguido_id=self.authors[0].id,
            )
        )
        base = datetime(2026, 8, 29, 18, 0, 0)
        posts = [
            Publicacion(
                autor_id=author.id,
                texto=f"Cursor post {author.id}",
                fecha=base - timedelta(minutes=index),
            )
            for index, author in enumerate(self.authors)
        ]
        posts.extend(
            [
                Publicacion(
                    autor_id=self.authors[1].id,
                    texto="Segunda publicación permitida",
                    fecha=base - timedelta(hours=1),
                ),
                Publicacion(
                    autor_id=self.authors[1].id,
                    texto="Tercera publicación excluida",
                    fecha=base - timedelta(hours=2),
                ),
            ]
        )
        self.db.add_all(posts)
        self.db.commit()
        self.eligible_ids = {post.id for post in posts[:-1]}
        self.excluded_third_id = posts[-1].id
        self.single_post_ids = {post.id for post in posts[:7]}
        self.service = FeedService(self.db)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _user(user_id: int, email: str) -> Usuario:
        return Usuario(
            id=user_id,
            email=email,
            nombre=f"User {user_id}",
            password_hash="not-used",
            headline="Feed cursor",
            ciudad="Buenos Aires",
        )

    def _collect_session(self, first_page, page_size: int) -> list[int]:
        ids = [item.id for item in first_page.items]
        page = first_page
        while page.has_more:
            self.assertIsNotNone(page.next_cursor)
            page = self.service.get_feed(
                self.viewer.id,
                cursor=page.next_cursor,
                page_size=page_size,
            )
            ids.extend(item.id for item in page.items)
        self.assertIsNone(page.next_cursor)
        return ids

    def test_cursor_traverses_every_candidate_once_and_ends_explicitly(self):
        first = self.service.get_feed(self.viewer.id, page_size=3)
        ids = self._collect_session(first, 3)

        self.assertEqual(set(ids), self.eligible_ids)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn(self.excluded_third_id, ids)

    def test_new_publication_after_first_page_is_deferred_to_a_new_session(self):
        first = self.service.get_feed(self.viewer.id, page_size=3)
        late = Publicacion(
            autor_id=self.late_author.id,
            texto="Publicada durante el scroll",
            fecha=datetime(2026, 8, 29, 19, 0, 0),
        )
        self.db.add(late)
        self.db.commit()

        current_session_ids = self._collect_session(first, 3)
        refreshed = self.service.get_feed(self.viewer.id, page_size=50)

        self.assertNotIn(late.id, current_session_ids)
        self.assertIn(late.id, [item.id for item in refreshed.items])
        self.assertEqual(set(current_session_ids), self.eligible_ids)

    def test_cursor_preserves_seed_and_social_snapshot_across_requests(self):
        with patch("src.services.feed_service.secrets.randbelow", return_value=111):
            first = self.service.get_feed(self.viewer.id, page_size=2)
        first_cursor = decode_feed_cursor(first.next_cursor)

        self.db.query(Seguimiento).delete()
        self.db.commit()
        with patch("src.services.feed_service.secrets.randbelow", return_value=999):
            second = self.service.get_feed(
                self.viewer.id,
                cursor=first.next_cursor,
                page_size=2,
            )
        second_cursor = decode_feed_cursor(second.next_cursor)

        self.assertEqual(first_cursor.seed, 111)
        self.assertEqual(second_cursor.seed, 111)
        self.assertEqual(
            first_cursor.social_author_ids,
            second_cursor.social_author_ids,
        )

    def test_repeating_the_same_cursor_returns_the_same_page(self):
        first = self.service.get_feed(self.viewer.id, page_size=2)
        repeated_a = self.service.get_feed(
            self.viewer.id,
            cursor=first.next_cursor,
            page_size=2,
        )
        repeated_b = self.service.get_feed(
            self.viewer.id,
            cursor=first.next_cursor,
            page_size=2,
        )
        self.assertEqual(
            [item.id for item in repeated_a.items],
            [item.id for item in repeated_b.items],
        )

    def test_invalid_tampered_and_cross_user_cursors_are_rejected(self):
        first = self.service.get_feed(self.viewer.id, page_size=2)
        with self.assertRaises(BadRequestError):
            self.service.get_feed(self.viewer.id, cursor="not-a-cursor", page_size=2)
        with self.assertRaises(BadRequestError):
            self.service.get_feed(
                self.viewer.id,
                cursor=f"{first.next_cursor}x",
                page_size=2,
            )
        with self.assertRaises(BadRequestError):
            self.service.get_feed(
                self.other_viewer.id,
                cursor=first.next_cursor,
                page_size=2,
            )

    def test_page_size_is_bounded_and_maximum_is_accepted(self):
        for invalid in (0, -1, 51, 1_000_000):
            with self.subTest(page_size=invalid):
                with self.assertRaises(BadRequestError):
                    self.service.get_feed(self.viewer.id, page_size=invalid)
        maximum = self.service.get_feed(self.viewer.id, page_size=50)
        self.assertEqual(set(item.id for item in maximum.items), self.eligible_ids)

    def test_pinned_publication_is_excluded_for_the_whole_session(self):
        pinned_id = next(iter(self.eligible_ids))
        first = self.service.get_feed(
            self.viewer.id,
            page_size=2,
            excluded_publicacion_id=pinned_id,
        )
        ids = self._collect_session(first, 2)
        self.assertNotIn(pinned_id, ids)
        self.assertEqual(set(ids), self.eligible_ids - {pinned_id})

    def test_deletion_between_pages_does_not_repeat_or_break_the_session(self):
        first = self.service.get_feed(self.viewer.id, page_size=2)
        first_ids = {item.id for item in first.items}
        deleted_id = next(iter(self.single_post_ids - first_ids))
        self.db.query(Publicacion).filter(Publicacion.id == deleted_id).delete()
        self.db.commit()

        ids = self._collect_session(first, 2)
        self.assertNotIn(deleted_id, ids)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(first_ids.issubset(ids))


@unittest.skipUnless(
    postgres_engine.dialect.name == "postgresql",
    "El snapshot concurrente requiere PostgreSQL.",
)
class FeedPostgresSnapshotTests(unittest.TestCase):
    def test_row_uncommitted_at_session_start_never_enters_later_pages(self):
        suffix = uuid4().hex
        user_ids: list[int] = []
        post_ids: list[int] = []
        with SessionLocal() as db:
            users = [
                Usuario(
                    email=f"feed-snapshot-{index}-{suffix}@example.com",
                    nombre=f"Snapshot {index}",
                    password_hash="not-used",
                    headline="Feed snapshot",
                    ciudad="Buenos Aires",
                )
                for index in range(8)
            ]
            db.add_all(users)
            db.flush()
            user_ids.extend(user.id for user in users)
            base = datetime(2026, 8, 30, 12, 0, 0)
            base_posts = [
                Publicacion(
                    autor_id=user.id,
                    texto=f"Snapshot base {index}",
                    fecha=base - timedelta(minutes=index),
                )
                for index, user in enumerate(users[:6])
            ]
            db.add_all(base_posts)
            db.commit()
            post_ids.extend(post.id for post in base_posts)
            viewer_id = users[0].id
            delayed_author_id = users[6].id
            committed_author_id = users[7].id

        delayed_ready = Event()
        allow_delayed_commit = Event()
        delayed_id: list[int] = []

        def insert_delayed() -> None:
            with SessionLocal() as db:
                delayed = Publicacion(
                    autor_id=delayed_author_id,
                    texto="Asignada antes del snapshot, confirmada después",
                    fecha=datetime(2026, 8, 30, 14, 0, 0),
                )
                db.add(delayed)
                db.flush()
                delayed_id.append(delayed.id)
                delayed_ready.set()
                allow_delayed_commit.wait(timeout=10)
                db.commit()

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(insert_delayed)
                self.assertTrue(delayed_ready.wait(timeout=5))

                with SessionLocal() as db:
                    committed = Publicacion(
                        autor_id=committed_author_id,
                        texto="Confirmada antes del snapshot",
                        fecha=datetime(2026, 8, 30, 13, 0, 0),
                    )
                    db.add(committed)
                    db.commit()
                    committed_id = committed.id
                    post_ids.append(committed_id)

                with SessionLocal() as db:
                    first = FeedService(db).get_feed(viewer_id, page_size=2)
                    first_cursor = decode_feed_cursor(first.next_cursor)
                self.assertIsNotNone(first_cursor.visibility_snapshot)

                allow_delayed_commit.set()
                pending.result(timeout=10)
                post_ids.extend(delayed_id)

            collected = [item.id for item in first.items]
            page = first
            while page.has_more:
                with SessionLocal() as db:
                    page = FeedService(db).get_feed(
                        viewer_id,
                        cursor=page.next_cursor,
                        page_size=20,
                    )
                collected.extend(item.id for item in page.items)

            self.assertIn(committed_id, collected)
            self.assertNotIn(delayed_id[0], collected)
            self.assertTrue(set(post_ids[:-2]).issubset(set(collected)))
            self.assertEqual(len(collected), len(set(collected)))
        finally:
            allow_delayed_commit.set()
            with SessionLocal() as db:
                if post_ids:
                    db.query(Publicacion).filter(
                        Publicacion.id.in_(post_ids)
                    ).delete(synchronize_session=False)
                db.query(Usuario).filter(Usuario.id.in_(user_ids)).delete(
                    synchronize_session=False
                )
                db.commit()


if __name__ == "__main__":
    unittest.main()
