import sys
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

# conftest.py está en: backend/alembic/versions/tests/conftest.py
#   parents[0] -> tests
#   parents[1] -> versions
#   parents[2] -> alembic
#   parents[3] -> backend      <-- lo que queremos
#   parents[4] -> radar-lab
BACKEND = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(BACKEND))


def _sqlite_path_for(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError(f"URL no SQLite: {url}")
    return Path(url[len(prefix):])


def _configure_sqlite_transactional(engine):

    @event.listens_for(engine, "connect")
    def _do_connect(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _do_begin(conn):
        conn.exec_driver_sql("BEGIN")


@pytest.fixture
def temp_db_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def sqlite_path(temp_db_url):
    return _sqlite_path_for(temp_db_url)


@pytest.fixture
def alembic_config(temp_db_url):
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("path_separator", "os")
    cfg.attributes["sqlalchemy_url_override"] = temp_db_url
    return cfg


@pytest.fixture
def failing_alembic_config(temp_db_url):
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("path_separator", "os")
    cfg.set_main_option("version_locations", str(FIXTURES / "versions_failing"))
    cfg.attributes["sqlalchemy_url_override"] = temp_db_url
    return cfg


@pytest.fixture
def engine(temp_db_url):
    e = create_engine(
        temp_db_url,
        poolclass=NullPool,
        connect_args={"isolation_level": None},
    )
    _configure_sqlite_transactional(e)
    yield e
    e.dispose()