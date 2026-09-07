"""Run the backend suite against a disposable local PostgreSQL database.

This module deliberately imports no ``src`` package before DATABASE_URL is replaced.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import psycopg2
from psycopg2 import sql


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
TEST_DATABASE_PREFIX = "atanes_test_"


def dotenv_database_url() -> str:
    for line in (BACKEND_DIRECTORY / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.removeprefix("DATABASE_URL=").strip()
    raise RuntimeError("DATABASE_URL no está configurada.")


def replace_database(url: str, database: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=f"/{database}"))


def main() -> int:
    source_url = os.environ.get("DATABASE_URL") or dotenv_database_url()
    parsed = urlparse(source_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise RuntimeError("La suite aislada requiere PostgreSQL.")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("La suite aislada sólo crea bases en PostgreSQL local.")

    test_database = f"{TEST_DATABASE_PREFIX}{uuid4().hex[:12]}"
    admin_url = replace_database(source_url, "postgres")
    test_url = replace_database(source_url, test_database)

    admin = psycopg2.connect(admin_url)
    try:
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_database)))
    finally:
        admin.close()

    try:
        with psycopg2.connect(test_url) as test_connection:
            with test_connection.cursor() as cursor:
                cursor.execute((BACKEND_DIRECTORY / "src/db/tables.sql").read_text(encoding="utf-8"))
            test_connection.commit()

        child_environment = os.environ.copy()
        child_environment["DATABASE_URL"] = test_url
        child_environment["ENVIRONMENT"] = "test"
        command = sys.argv[1:] or [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ]
        result = subprocess.run(
            command,
            cwd=BACKEND_DIRECTORY,
            env=child_environment,
            check=False,
        )
        return result.returncode
    finally:
        if not test_database.startswith(TEST_DATABASE_PREFIX):
            raise RuntimeError("Nombre de base temporal inesperado; limpieza abortada.")
        admin = psycopg2.connect(admin_url)
        try:
            admin.autocommit = True
            with admin.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (test_database,),
                )
                cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(test_database)))
        finally:
            admin.close()


if __name__ == "__main__":
    raise SystemExit(main())
