import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import app
from src.db.connection import Base, engine as postgres_engine, get_db
from src.db.models.publicacion_model import Publicacion
from src.db.models.publicacion_multimedia_model import PublicacionMultimedia
from src.db.models.usuario_model import Usuario
from src.dtos.publicacion_dto import CreatePublicacionMultimediaDTO
from src.middlewares.auth_middleware import get_current_user
from src.services.publicacion_service import PublicacionService
from src.utils import publication_media_storage
from src.utils.publication_media_storage import UploadedPublicationFile


def png_bytes(color: str = "green") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (3, 3), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def mp4_bytes(marker: bytes = b"video") -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom" + marker


class PublicationMultimediaApiTests(unittest.TestCase):
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
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory_patch = patch.object(
            publication_media_storage,
            "PUBLICATION_MEDIA_DIRECTORY",
            Path(self.temporary_directory.name),
        )
        self.directory_patch.start()
        self.addCleanup(self.directory_patch.stop)
        self.db = self.SessionLocal()
        self.user = self._create_user("author@example.com", "Author")
        self.other = self._create_user("other@example.com", "Other")
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

    def _create_user(self, email: str, name: str) -> Usuario:
        user = Usuario(
            email=email,
            nombre=name,
            password_hash="not-used",
            headline="Backend",
            ciudad="Argentina, Buenos Aires",
        )
        self.db.add(user)
        self.db.flush()
        return user

    def _create_media_post(self, files, text: str = ""):
        return self.client.post(
            "/api/publicaciones/multimedia",
            data={"texto": text},
            files=[("archivos", file) for file in files],
        )

    def test_text_only_publications_keep_the_existing_contract(self):
        response = self.client.post("/api/publicaciones", json={"texto": "Solo texto"})

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["texto"], "Solo texto")
        self.assertEqual(response.json()["multimedia"], [])

    def test_image_only_is_stored_with_a_safe_publication_name(self):
        response = self._create_media_post(
            [("../../original.png", png_bytes(), "image/png")]
        )

        self.assertEqual(response.status_code, 400, response.text)
        accepted = self._create_media_post(
            [("original.png", png_bytes(), "image/png")]
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        media = accepted.json()["multimedia"][0]
        self.assertEqual(media["tipo"], "IMAGEN")
        filename = Path(media["ruta"]).name
        self.assertRegex(filename, rf"^publicacion_{accepted.json()['id']}_[0-9a-f]{{32}}\.png$")
        self.assertTrue((publication_media_storage.PUBLICATION_MEDIA_DIRECTORY / filename).exists())

    def test_video_only_and_multiple_videos_are_supported(self):
        response = self._create_media_post(
            [
                ("one.mp4", mp4_bytes(b"one"), "video/mp4"),
                ("two.mp4", mp4_bytes(b"two"), "video/mp4"),
            ]
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual([item["tipo"] for item in response.json()["multimedia"]], ["VIDEO", "VIDEO"])

    def test_multiple_images_are_supported(self):
        response = self._create_media_post(
            [
                ("one.png", png_bytes("red"), "image/png"),
                ("two.png", png_bytes("green"), "image/png"),
                ("three.png", png_bytes("blue"), "image/png"),
            ]
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual([item["tipo"] for item in response.json()["multimedia"]], ["IMAGEN", "IMAGEN", "IMAGEN"])
        self.assertEqual([item["orden"] for item in response.json()["multimedia"]], [0, 1, 2])

    def test_mixed_media_and_text_preserve_upload_order(self):
        response = self._create_media_post(
            [
                ("first.png", png_bytes("red"), "image/png"),
                ("second.mp4", mp4_bytes(), "video/mp4"),
                ("third.png", png_bytes("blue"), "image/png"),
            ],
            text="Texto y multimedia",
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["texto"], "Texto y multimedia")
        self.assertEqual([item["tipo"] for item in body["multimedia"]], ["IMAGEN", "VIDEO", "IMAGEN"])
        self.assertEqual([item["orden"] for item in body["multimedia"]], [0, 1, 2])

    def test_update_null_text_is_safe_for_a_media_only_publication(self):
        created = self._create_media_post(
            [("media-only.png", png_bytes(), "image/png")]
        ).json()

        response = self.client.put(
            f"/api/publicaciones/{created['id']}",
            json={"texto": None},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["texto"], "")
        self.assertEqual(self.db.get(Publicacion, created["id"]).texto, "")

    def test_update_null_text_without_media_is_rejected_without_a_500(self):
        created = self.client.post(
            "/api/publicaciones",
            json={"texto": "Publicación con texto"},
        ).json()

        response = self.client.put(
            f"/api/publicaciones/{created['id']}",
            json={"texto": None},
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.db.get(Publicacion, created["id"]).texto, "Publicación con texto")

    def test_update_whitespace_only_text_is_rejected(self):
        created = self.client.post(
            "/api/publicaciones",
            json={"texto": "Texto válido"},
        ).json()

        response = self.client.put(
            f"/api/publicaciones/{created['id']}",
            json={"texto": " \t\n "},
        )

        self.assertEqual(response.status_code, 422, response.text)

    def test_multimedia_update_rejects_whitespace_text_even_with_media(self):
        created = self._create_media_post(
            [("media.png", png_bytes(), "image/png")]
        ).json()

        response = self.client.put(
            f"/api/publicaciones/{created['id']}/multimedia",
            data={
                "texto": " \t ",
                "conservar_multimedia_id": str(created["multimedia"][0]["id"]),
            },
        )

        self.assertEqual(response.status_code, 400, response.text)

    def test_invalid_files_and_empty_publications_are_rejected(self):
        invalid = self._create_media_post(
            [("not-video.mp4", b"plain text", "video/mp4")]
        )
        empty = self.client.post("/api/publicaciones/multimedia", data={"texto": "   "})

        self.assertEqual(invalid.status_code, 400, invalid.text)
        self.assertEqual(empty.status_code, 400, empty.text)
        self.assertEqual(self.db.query(Publicacion).count(), 0)

    def test_file_count_limit_is_enforced_before_persistence(self):
        response = self._create_media_post(
            [
                (f"image-{index}.png", png_bytes(), "image/png")
                for index in range(11)
            ]
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.db.query(Publicacion).count(), 0)

    def test_outsider_cannot_edit_media_or_create_files(self):
        created = self._create_media_post(
            [("mine.png", png_bytes(), "image/png")]
        ).json()
        before = set(publication_media_storage.PUBLICATION_MEDIA_DIRECTORY.iterdir())
        app.dependency_overrides[get_current_user] = lambda: self.other

        response = self.client.put(
            f"/api/publicaciones/{created['id']}/multimedia",
            data={"texto": "Ajena"},
            files=[("archivos", ("new.png", png_bytes("blue"), "image/png"))],
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(set(publication_media_storage.PUBLICATION_MEDIA_DIRECTORY.iterdir()), before)

    def test_edit_can_keep_remove_and_add_media_without_losing_order(self):
        created = self._create_media_post(
            [
                ("first.png", png_bytes("red"), "image/png"),
                ("second.png", png_bytes("green"), "image/png"),
            ]
        ).json()
        first_path = publication_media_storage.PUBLICATION_MEDIA_DIRECTORY / Path(created["multimedia"][0]["ruta"]).name
        second_path = publication_media_storage.PUBLICATION_MEDIA_DIRECTORY / Path(created["multimedia"][1]["ruta"]).name

        response = self.client.put(
            f"/api/publicaciones/{created['id']}/multimedia",
            data={"texto": "Editada", "conservar_multimedia_id": str(created["multimedia"][1]["id"])},
            files=[("archivos", ("new.mp4", mp4_bytes(), "video/mp4"))],
        )

        self.assertEqual(response.status_code, 200, response.text)
        media = response.json()["multimedia"]
        self.assertEqual([item["id"] for item in media[:1]], [created["multimedia"][1]["id"]])
        self.assertEqual([item["tipo"] for item in media], ["IMAGEN", "VIDEO"])
        self.assertEqual([item["orden"] for item in media], [0, 1])
        self.assertFalse(first_path.exists())
        self.assertTrue(second_path.exists())

    def test_delete_removes_only_the_target_publication_files(self):
        first = self._create_media_post(
            [("first.png", png_bytes("red"), "image/png")]
        ).json()
        second = self._create_media_post(
            [("second.png", png_bytes("blue"), "image/png")]
        ).json()
        first_path = publication_media_storage.PUBLICATION_MEDIA_DIRECTORY / Path(first["multimedia"][0]["ruta"]).name
        second_path = publication_media_storage.PUBLICATION_MEDIA_DIRECTORY / Path(second["multimedia"][0]["ruta"]).name

        response = self.client.delete(f"/api/publicaciones/{first['id']}")

        self.assertEqual(response.status_code, 204, response.text)
        self.assertFalse(first_path.exists())
        self.assertTrue(second_path.exists())
        self.assertIsNone(self.db.get(Publicacion, first["id"]))
        self.assertIsNotNone(self.db.get(PublicacionMultimedia, second["multimedia"][0]["id"]))

    def test_old_publication_without_media_is_still_readable(self):
        post = Publicacion(autor_id=self.user.id, texto="Histórica")
        self.db.add(post)
        self.db.commit()

        response = self.client.get(f"/api/publicaciones/{post.id}")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["multimedia"], [])


class PublicationMultimediaRollbackTests(unittest.TestCase):
    def test_database_failure_removes_new_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            publication_media_storage,
            "PUBLICATION_MEDIA_DIRECTORY",
            Path(directory),
        ):
            db = Mock()
            db.commit.side_effect = RuntimeError("db failure")
            service = PublicacionService(db)
            service.usuario_repository = Mock()
            service.usuario_repository.get_by_id.return_value = SimpleNamespace(id=7)
            service.repository = Mock()
            service.repository.create.return_value = SimpleNamespace(id=42)
            upload = UploadedPublicationFile(
                filename="photo.png",
                content_type="image/png",
                content=png_bytes(),
            )

            with self.assertRaisesRegex(RuntimeError, "db failure"):
                service.create_with_multimedia(
                    CreatePublicacionMultimediaDTO(autor_id=7, texto=""),
                    [upload],
                )

            db.rollback.assert_called_once_with()
            self.assertEqual(list(Path(directory).iterdir()), [])


class PublicationMultimediaSchemaTests(unittest.TestCase):
    def test_model_bootstrap_and_incremental_migration_stay_synchronized(self):
        indexes = {index.name for index in PublicacionMultimedia.__table__.indexes}
        constraints = {
            constraint.name for constraint in PublicacionMultimedia.__table__.constraints
        }
        tables_sql = Path("src/db/tables.sql").read_text(encoding="utf-8")
        migration_sql = Path(
            "src/db/migrations/20260907_publication_multimedia.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("idx_publicacion_multimedia_publicacion", indexes)
        self.assertIn("uq_publicacion_multimedia_orden", constraints)
        for source in (tables_sql, migration_sql):
            self.assertIn("CREATE TABLE publicacion_multimedia", source)
            self.assertIn("ON DELETE CASCADE", source)
            self.assertIn("uq_publicacion_multimedia_orden", source)
            self.assertNotIn("BYTEA", source.upper())


@unittest.skipUnless(
    os.environ.get("ENVIRONMENT") == "test"
    and (postgres_engine.url.database or "").startswith("atanes_test_"),
    "requiere la base PostgreSQL temporal del runner aislado",
)
class PublicationMultimediaMigrationTests(unittest.TestCase):
    def test_incremental_migration_preserves_existing_publications(self):
        schema = f"migration_media_{uuid4().hex[:12]}"
        migration = Path(
            "src/db/migrations/20260907_publication_multimedia.sql"
        ).read_text(encoding="utf-8")
        connection = postgres_engine.raw_connection()
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE SCHEMA "{schema}"')
                cursor.execute(f'SET search_path TO "{schema}"')
                cursor.execute(
                    "CREATE TABLE publicacion ("
                    "id SERIAL PRIMARY KEY, autor_id INT NOT NULL, "
                    "texto VARCHAR(3000) NOT NULL, "
                    "fecha TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                    "CONSTRAINT check_longitud_texto CHECK ("
                    "LENGTH(texto) BETWEEN 1 AND 3000 "
                    "AND texto ~ '[^[:space:]]'))"
                )
                cursor.execute(
                    "INSERT INTO publicacion (autor_id, texto) VALUES (%s, %s)",
                    (19, "Publicación histórica"),
                )
                cursor.execute(migration)
                cursor.execute("SELECT texto FROM publicacion ORDER BY id")
                self.assertEqual(cursor.fetchall(), [("Publicación histórica",)])
                cursor.execute(
                    "INSERT INTO publicacion (autor_id, texto) VALUES (%s, %s) RETURNING id",
                    (20, ""),
                )
                publication_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO publicacion_multimedia "
                    "(publicacion_id, ruta, tipo, orden) VALUES (%s, %s, %s, %s)",
                    (publication_id, "/multimedia_publicaciones/test.png", "IMAGEN", 0),
                )
                cursor.execute(
                    "SELECT tipo, orden FROM publicacion_multimedia "
                    "WHERE publicacion_id = %s",
                    (publication_id,),
                )
                self.assertEqual(cursor.fetchone(), ("IMAGEN", 0))
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET search_path")
            connection.close()


if __name__ == "__main__":
    unittest.main()
