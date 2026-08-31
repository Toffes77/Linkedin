import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from PIL import Image

from src.services.usuario_service import UsuarioService
from src.utils import image_storage
from src.utils.errors import BadRequestError


def png_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeUpload:
    def __init__(self, content: bytes):
        self.content = content
        self.requested_size: int | None = None

    async def read(self, size: int = -1) -> bytes:
        self.requested_size = size
        return self.content[:size]


class UploadReadSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_reader_caps_the_single_read_and_rejects_oversized_upload(self):
        upload = FakeUpload(b"x" * (image_storage.MAX_IMAGE_SIZE_BYTES + 1))

        with self.assertRaises(BadRequestError):
            await image_storage.read_limited_upload(upload)

        self.assertEqual(
            upload.requested_size,
            image_storage.MAX_IMAGE_SIZE_BYTES + 1,
        )

    async def test_reader_accepts_content_within_limit(self):
        upload = FakeUpload(b"small")

        content = await image_storage.read_limited_upload(upload)

        self.assertEqual(content, b"small")


class VersionedImageStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory_patch = patch.object(
            image_storage,
            "IMAGES_DIRECTORY",
            Path(self.temporary_directory.name),
        )
        self.directory_patch.start()
        self.addCleanup(self.directory_patch.stop)

    def test_replacing_an_image_uses_a_new_name_and_preserves_previous_content(self):
        first_url = image_storage.save_image("usuario", 17, ".png", b"first")
        second_url = image_storage.save_image("usuario", 17, ".png", b"second")

        self.assertNotEqual(first_url, second_url)
        first_path = image_storage.IMAGES_DIRECTORY / first_url.removeprefix("/imagenes/")
        second_path = image_storage.IMAGES_DIRECTORY / second_url.removeprefix("/imagenes/")
        self.assertEqual(first_path.read_bytes(), b"first")
        self.assertEqual(second_path.read_bytes(), b"second")

    def test_database_failure_removes_new_file_without_overwriting_previous_file(self):
        previous_url = image_storage.save_image("usuario", 23, ".png", png_bytes("red"))
        previous_path = (
            image_storage.IMAGES_DIRECTORY / previous_url.removeprefix("/imagenes/")
        )
        previous_content = previous_path.read_bytes()
        usuario = SimpleNamespace(id=23, foto_perfil_url=previous_url)
        db = Mock()
        db.commit.side_effect = RuntimeError("db failure")
        service = UsuarioService(db)
        service.repository = Mock()
        service.repository.get_by_id.return_value = usuario
        service.repository.update_profile_photo.return_value = usuario

        with self.assertRaisesRegex(RuntimeError, "db failure"):
            service.update_profile_photo(23, "replacement.png", png_bytes("blue"))

        service.repository.update_profile_photo.assert_called_once_with(
            usuario,
            ANY,
            commit=False,
        )
        db.rollback.assert_called_once_with()
        self.assertEqual(previous_path.read_bytes(), previous_content)
        remaining = list(image_storage.IMAGES_DIRECTORY.iterdir())
        self.assertEqual(remaining, [previous_path])

    def test_cleanup_accepts_legacy_names_but_rejects_other_entities(self):
        legacy = image_storage.IMAGES_DIRECTORY / "usuario_31.jpg"
        foreign = image_storage.IMAGES_DIRECTORY / "usuario_32.jpg"
        legacy.write_bytes(b"legacy")
        foreign.write_bytes(b"foreign")

        image_storage.delete_managed_image("/imagenes/usuario_31.jpg", "usuario", 31)
        image_storage.delete_managed_image("/imagenes/usuario_32.jpg", "usuario", 31)

        self.assertFalse(legacy.exists())
        self.assertTrue(foreign.exists())


if __name__ == "__main__":
    unittest.main()
