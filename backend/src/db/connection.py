from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.env import settings
from src.db.test_safety import assert_safe_test_database_url, is_test_process

if is_test_process():
    assert_safe_test_database_url(settings.DATABASE_URL)

engine_options = {}
if settings.DATABASE_URL.startswith(("postgresql", "postgres")):
    engine_options["connect_args"] = {"options": "-c timezone=UTC"}

engine = create_engine(settings.DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """Dependency de FastAPI: abre una sesión por request y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
