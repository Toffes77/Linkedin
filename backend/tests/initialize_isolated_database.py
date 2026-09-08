"""Inicializa una base temporal usando los modelos, nunca tables.sql."""

from src.app import app  # noqa: F401 - importa todos los modelos registrados.
from sqlalchemy import text
from src.db.connection import Base, engine
from src.db.test_safety import assert_safe_test_database_url
from src.config.env import settings


assert_safe_test_database_url(settings.DATABASE_URL)
with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
Base.metadata.create_all(bind=engine)
