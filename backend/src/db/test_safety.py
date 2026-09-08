"""Protecciones para impedir que una suite de pruebas use la base principal."""

import os
import sys
from urllib.parse import urlparse


TEST_DATABASE_PREFIX = "atanes_test_"


def is_test_process() -> bool:
    """Indica si el proceso actual fue iniciado por un runner de pruebas."""
    return (
        os.getenv("ENVIRONMENT", "").lower() == "test"
        or "unittest" in sys.modules
        or "pytest" in sys.modules
    )


def assert_safe_test_database_url(database_url: str) -> None:
    """Falla antes de crear un engine de pruebas contra una base no aislada."""
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        return

    database_name = parsed.path.lstrip("/")
    if not database_name.startswith(TEST_DATABASE_PREFIX):
        raise RuntimeError(
            "Las pruebas PostgreSQL deben usar una base temporal con prefijo "
            f"{TEST_DATABASE_PREFIX}; se rechazó la base configurada."
        )
