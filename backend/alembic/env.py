import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, event, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_override_url = config.attributes.get("sqlalchemy_url_override")
config.set_main_option("sqlalchemy.url", _override_url or settings.DATABASE_URL)

target_metadata = Base.metadata


def _configure_sqlite_transactional(engine):

    @event.listens_for(engine, "connect")
    def _do_connect(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _do_begin(conn):
        conn.exec_driver_sql("BEGIN")


def _sqlite_cursor(connection):
    return connection.connection.dbapi_connection.cursor()


def _sqlite_pragma(connection, value):
    cur = _sqlite_cursor(connection)
    try:
        cur.execute(f"PRAGMA foreign_keys={value}")
    finally:
        cur.close()


def _sqlite_read_pragma(connection):
    cur = _sqlite_cursor(connection)
    try:
        return cur.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        cur.close()


def _sqlite_tmp_tables(connection):
    prefix = "_alembic_tmp_"
    cur = _sqlite_cursor(connection)
    try:
        return [
            r[0] for r in cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND substr(name, 1, ?) = ?",
                (len(prefix), prefix),
            ).fetchall()
        ]
    finally:
        cur.close()


def _run_migrations(connection, is_sqlite):
    if is_sqlite:
        config.attributes["_dbapi_used_id"] = id(
            connection.connection.dbapi_connection
        )

    try:
        if is_sqlite:
            _sqlite_pragma(connection, "OFF")
            if _sqlite_read_pragma(connection) != 0:
                raise RuntimeError(
                    "No se pudo desactivar PRAGMA foreign_keys antes de la migración"
                )
            tmp = _sqlite_tmp_tables(connection)
            if tmp:
                raise RuntimeError(
                    f"Tablas temporales de Alembic detectadas: {tmp}. "
                    "Inspecciona su contenido y elimínalas manualmente solo si "
                    "confirmas que no contienen datos necesarios. "
                    "La migración no se ha ejecutado."
                )

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
            transactional_ddl=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
    finally:
        if is_sqlite:
            original_exc = sys.exc_info()[1]
            restore_exc = None
            final_state = None
            try:
                _sqlite_pragma(connection, "ON")
                final_state = _sqlite_read_pragma(connection)
            except Exception as e:
                restore_exc = e

            config.attributes["_final_fk_state"] = final_state

            if final_state != 1:
                msg = (
                    "PRAGMA foreign_keys no restaurado correctamente "
                    f"(estado final: {final_state!r})"
                )
                if restore_exc is not None:
                    msg += f"; error de restauración: {restore_exc!r}"
                if original_exc is not None:
                    original_exc.add_note(msg)
                else:
                    if restore_exc is not None:
                        raise RuntimeError(msg) from restore_exc
                    raise RuntimeError(msg)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    injected = config.attributes.get("connection")
    if injected is not None:
        _run_migrations(injected, injected.dialect.name == "sqlite")
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    if connectable.dialect.name == "sqlite":
        _configure_sqlite_transactional(connectable)

    with connectable.connect() as connection:
        _run_migrations(connection, connection.dialect.name == "sqlite")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()