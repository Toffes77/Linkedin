from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.db.models.publicacion_multimedia_model import TipoMultimedia
from src.utils.errors import BadRequestError
from src.utils.image_storage import MAX_IMAGE_SIZE_BYTES, validate_and_get_extension


MAX_PUBLICATION_MEDIA_ITEMS = 10
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_MEDIA_SIZE_BYTES = 150 * 1024 * 1024
_MAX_READ_SIZE_BYTES = MAX_VIDEO_SIZE_BYTES
_BACKEND_DIR = Path(__file__).resolve().parents[2]
PUBLICATION_MEDIA_DIRECTORY = _BACKEND_DIR / "multimedia_publicaciones"
_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
_VIDEO_MIME_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
_GENERATED_EXTENSIONS = {".jpg", ".png", ".webp", ".mp4", ".webm"}


@dataclass(frozen=True)
class UploadedPublicationFile:
    filename: str | None
    content_type: str | None
    content: bytes


@dataclass(frozen=True)
class ValidatedPublicationFile:
    extension: str
    media_type: TipoMultimedia
    content: bytes


async def read_publication_upload(upload: UploadFile) -> UploadedPublicationFile:
    extension = Path(upload.filename or "").suffix.lower()
    read_limit = MAX_IMAGE_SIZE_BYTES if extension in {".jpg", ".jpeg", ".png", ".webp"} else _MAX_READ_SIZE_BYTES
    content = await upload.read(read_limit + 1)
    if len(content) > read_limit:
        if read_limit == MAX_IMAGE_SIZE_BYTES:
            raise BadRequestError("Cada imagen puede ocupar como máximo 5 MiB.")
        raise BadRequestError("Cada video puede ocupar como máximo 50 MiB.")
    return UploadedPublicationFile(
        filename=upload.filename,
        content_type=upload.content_type,
        content=content,
    )


async def read_publication_uploads(
    uploads: list[UploadFile],
) -> list[UploadedPublicationFile]:
    if len(uploads) > MAX_PUBLICATION_MEDIA_ITEMS:
        raise BadRequestError(
            f"Una publicación puede incluir hasta {MAX_PUBLICATION_MEDIA_ITEMS} archivos."
        )
    files: list[UploadedPublicationFile] = []
    total_size = 0
    for upload in uploads:
        file = await read_publication_upload(upload)
        total_size += len(file.content)
        if total_size > MAX_TOTAL_MEDIA_SIZE_BYTES:
            raise BadRequestError("El multimedia de la publicación supera los 150 MiB.")
        files.append(file)
    return files


def validate_publication_files(
    files: list[UploadedPublicationFile],
) -> list[ValidatedPublicationFile]:
    if len(files) > MAX_PUBLICATION_MEDIA_ITEMS:
        raise BadRequestError(
            f"Una publicación puede incluir hasta {MAX_PUBLICATION_MEDIA_ITEMS} archivos."
        )
    if sum(len(file.content) for file in files) > MAX_TOTAL_MEDIA_SIZE_BYTES:
        raise BadRequestError("El multimedia de la publicación supera los 150 MiB.")
    return [validate_publication_file(file) for file in files]


def validate_publication_file(
    file: UploadedPublicationFile,
) -> ValidatedPublicationFile:
    if not file.filename:
        raise BadRequestError("Todos los archivos deben incluir un nombre.")

    supplied_path = Path(file.filename)
    if file.filename != supplied_path.name or ".." in supplied_path.parts:
        raise BadRequestError("El nombre del archivo no es válido.")

    extension = supplied_path.suffix.lower()
    if extension in {".jpg", ".jpeg", ".png", ".webp"}:
        if file.content_type not in _IMAGE_MIME_TYPES:
            raise BadRequestError("El tipo MIME de la imagen no está permitido.")
        canonical_extension = validate_and_get_extension(file.filename, file.content)
        return ValidatedPublicationFile(
            extension=canonical_extension,
            media_type=TipoMultimedia.IMAGEN,
            content=file.content,
        )

    if extension in {".mp4", ".webm"}:
        if not file.content:
            raise BadRequestError("El archivo de video está vacío.")
        if len(file.content) > MAX_VIDEO_SIZE_BYTES:
            raise BadRequestError("Cada video puede ocupar como máximo 50 MiB.")
        expected_extension = _VIDEO_MIME_TYPES.get(file.content_type or "")
        if expected_extension != extension:
            raise BadRequestError("La extensión no coincide con el tipo MIME del video.")
        if extension == ".mp4" and not _is_mp4(file.content):
            raise BadRequestError("El archivo no es un video MP4 válido.")
        if extension == ".webm" and not file.content.startswith(b"\x1aE\xdf\xa3"):
            raise BadRequestError("El archivo no es un video WebM válido.")
        return ValidatedPublicationFile(
            extension=extension,
            media_type=TipoMultimedia.VIDEO,
            content=file.content,
        )

    raise BadRequestError("El formato del archivo no está permitido.")


def save_publication_file(
    publication_id: int,
    file: ValidatedPublicationFile,
) -> str:
    PUBLICATION_MEDIA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    filename = f"publicacion_{publication_id}_{uuid4().hex}{file.extension}"
    destination = PUBLICATION_MEDIA_DIRECTORY / filename
    temporary_destination = PUBLICATION_MEDIA_DIRECTORY / f".{filename}.tmp"
    try:
        temporary_destination.write_bytes(file.content)
        temporary_destination.replace(destination)
    except OSError:
        temporary_destination.unlink(missing_ok=True)
        raise
    return f"/multimedia_publicaciones/{filename}"


def delete_publication_file(path: str | None, publication_id: int) -> None:
    if not path or not path.startswith("/multimedia_publicaciones/"):
        return

    filename = path.removeprefix("/multimedia_publicaciones/")
    supplied_path = Path(filename)
    if filename != supplied_path.name or supplied_path.suffix.lower() not in _GENERATED_EXTENSIONS:
        return
    if not supplied_path.stem.startswith(f"publicacion_{publication_id}_"):
        return

    try:
        (PUBLICATION_MEDIA_DIRECTORY / filename).unlink(missing_ok=True)
    except OSError:
        pass


def _is_mp4(content: bytes) -> bool:
    return len(content) >= 12 and content[4:8] == b"ftyp"
