import base64
import json
from typing import Any


CURSOR_VERSION = 1


def encode_cursor(
    kind: str,
    scope: dict[str, Any],
    values: list[Any],
) -> str:
    payload = {
        "v": CURSOR_VERSION,
        "kind": kind,
        "scope": scope,
        "values": values,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(
    value: str,
    *,
    expected_kind: str,
    expected_scope: dict[str, Any],
) -> list[Any]:
    try:
        padding = "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(value + padding)
        payload = json.loads(raw)
    except Exception as exc:
        raise ValueError("Cursor inválido.") from exc

    if (
        not isinstance(payload, dict)
        or payload.get("v") != CURSOR_VERSION
        or payload.get("kind") != expected_kind
        or payload.get("scope") != expected_scope
        or not isinstance(payload.get("values"), list)
    ):
        raise ValueError("El cursor no corresponde a esta consulta.")
    return payload["values"]
