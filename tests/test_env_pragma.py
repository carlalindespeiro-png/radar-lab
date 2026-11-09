import sqlite3

import pytest
from alembic import command


def test_p1_fk_restored_after_successful_upgrade(alembic_config, engine):
    with engine.connect() as conn:
        alembic_config.attributes["connection"] = conn
        command.upgrade(alembic_config, "0006")

        assert alembic_config.attributes["_final_fk_state"] == 1

        cur = conn.connection.dbapi_connection.cursor()
        try:
            cols = {r[1] for r in cur.execute("PRAGMA table_info(evidence)").fetchall()}
            required = {"assertion_id", "source_id", "extract_id", "excerpt"}
            assert required.issubset(cols), (
                f"Columnas esperadas ausentes en evidence: {required - cols}"
            )
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute(
                    "INSERT INTO evidence "
                    "(assertion_id, source_id, extract_id, excerpt) "
                    "VALUES (999999, 999999, 999999, 'x')"
                )
        finally:
            cur.close()
            conn.connection.dbapi_connection.rollback()


def test_p2_fk_restored_after_failed_migration(failing_alembic_config, engine):
    with engine.connect() as conn:
        conn.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE child ("
            "id INTEGER PRIMARY KEY, "
            "parent_id INTEGER NOT NULL REFERENCES parent(id)"
            ")"
        )
        conn.commit()

        failing_alembic_config.attributes["connection"] = conn
        with pytest.raises(RuntimeError, match="migración ficticia forzada a fallar"):
            command.upgrade(failing_alembic_config, "head")

        assert failing_alembic_config.attributes["_final_fk_state"] == 1

        cur = conn.connection.dbapi_connection.cursor()
        try:
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute("INSERT INTO child (id, parent_id) VALUES (1, 999)")
        finally:
            cur.close()
            conn.connection.dbapi_connection.rollback()


def test_p4_tmp_table_aborts_without_deleting(alembic_config, engine, sqlite_path):
    command.upgrade(alembic_config, "0005_add_research_run_sources_and_extract_status")

    con = sqlite3.connect(sqlite_path)
    con.execute("CREATE TABLE _alembic_tmp_evidence (x INTEGER)")
    con.commit()
    con.close()

    with engine.connect() as conn:
        alembic_config.attributes["connection"] = conn
        with pytest.raises(RuntimeError, match="Tablas temporales de Alembic detectadas"):
            command.upgrade(alembic_config, "0006")

        assert alembic_config.attributes["_final_fk_state"] == 1

        cur = conn.connection.dbapi_connection.cursor()
        try:
            exists = cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='_alembic_tmp_evidence'"
            ).fetchone()
        finally:
            cur.close()
        assert exists is not None