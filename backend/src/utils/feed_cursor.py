import base64
import binascii
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime

from src.config.env import settings


CURSOR_VERSION = 1
MAX_CURSOR_LENGTH = 65_536
SNAPSHOT_PATTERN = re.compile(r"^\d+:\d+:(?:\d+(?:,\d+)*)?$")


@dataclass(frozen=True)
class FeedPosition:
    day_key: int
    is_social: int
    jitter: int
    fecha: datetime
    publicacion_id: int


@dataclass(frozen=True)
class FeedCursor:
    usuario_id: int
    seed: int
    snapshot_max_id: int
    visibility_snapshot: str | None
    social_author_ids: tuple[int, ...]
    excluded_publicacion_id: int | None
    position: FeedPosition


def encode_feed_cursor(cursor: FeedCursor) -> str:
    payload = {
        "v": CURSOR_VERSION,
        "uid": cursor.usuario_id,
        "seed": cursor.seed,
        "max": cursor.snapshot_max_id,
        "snapshot": cursor.visibility_snapshot,
        "social": list(cursor.social_author_ids),
        "exclude": cursor.excluded_publicacion_id,
        "day": cursor.position.day_key,
        "lane": cursor.position.is_social,
        "jitter": cursor.position.jitter,
        "fecha": cursor.position.fecha.isoformat(),
        "id": cursor.position.publicacion_id,
    }
    encoded_payload = _base64_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_base64_encode(signature)}"


def decode_feed_cursor(value: str) -> FeedCursor:
    if not value or len(value) > MAX_CURSOR_LENGTH:
        raise ValueError("Cursor inválido.")
    try:
        encoded_payload, encoded_signature = value.split(".", maxsplit=1)
        expected = hmac.new(
            settings.JWT_SECRET.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual = _base64_decode(encoded_signature)
        if not hmac.compare_digest(actual, expected):
            raise ValueError("Firma inválida.")
        payload = json.loads(_base64_decode(encoded_payload))
        return _parse_payload(payload)
    except (
        binascii.Error,
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("Cursor inválido.") from exc


def _parse_payload(payload: object) -> FeedCursor:
    if not isinstance(payload, dict) or payload.get("v") != CURSOR_VERSION:
        raise ValueError("Versión de cursor inválida.")

    usuario_id = _positive_int(payload.get("uid"))
    seed = _non_negative_int(payload.get("seed"))
    snapshot_max_id = _non_negative_int(payload.get("max"))
    raw_snapshot = payload.get("snapshot")
    if raw_snapshot is not None and (
        not isinstance(raw_snapshot, str)
        or not SNAPSHOT_PATTERN.fullmatch(raw_snapshot)
    ):
        raise ValueError("Snapshot inválido.")
    publicacion_id = _positive_int(payload.get("id"))
    day_key = _positive_int(payload.get("day"))
    jitter = _int(payload.get("jitter"))
    is_social = _int(payload.get("lane"))
    if is_social not in (0, 1) or not -7 <= jitter <= 7:
        raise ValueError("Posición inválida.")

    raw_social = payload.get("social")
    if not isinstance(raw_social, list) or len(raw_social) > 10_000:
        raise ValueError("Autores sociales inválidos.")
    social_author_ids = tuple(_positive_int(value) for value in raw_social)
    if len(set(social_author_ids)) != len(social_author_ids):
        raise ValueError("Autores sociales duplicados.")

    excluded = payload.get("exclude")
    excluded_publicacion_id = None if excluded is None else _positive_int(excluded)
    raw_fecha = payload.get("fecha")
    if not isinstance(raw_fecha, str):
        raise ValueError("Fecha inválida.")
    fecha = datetime.fromisoformat(raw_fecha)

    return FeedCursor(
        usuario_id=usuario_id,
        seed=seed,
        snapshot_max_id=snapshot_max_id,
        visibility_snapshot=raw_snapshot,
        social_author_ids=social_author_ids,
        excluded_publicacion_id=excluded_publicacion_id,
        position=FeedPosition(
            day_key=day_key,
            is_social=is_social,
            jitter=jitter,
            fecha=fecha,
            publicacion_id=publicacion_id,
        ),
    )


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Entero inválido.")
    return value


def _positive_int(value: object) -> int:
    parsed = _int(value)
    if parsed < 1:
        raise ValueError("Entero positivo inválido.")
    return parsed


def _non_negative_int(value: object) -> int:
    parsed = _int(value)
    if parsed < 0:
        raise ValueError("Entero no negativo inválido.")
    return parsed


def _base64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
