import sqlite3
import pytest
from alembic import command
def test_columns_created(alembic_config, sqlite_path):
    """14 columnas nuevas: 5 evidence + 3 assertions + 5 problems + 1 research_runs."""
    command.upgrade(alembic_config, "0006")
    con = sqlite3.connect(sqlite_path)
    cur = con.cursor()
    ev = {r[1] for r in cur.execute("PRAGMA table_info(evidence)").fetchall()}
    for c in ("clasificacion_evidencia", "limitaciones_evidencia",
              "posicion_inicio", "posicion_fin", "cita_hash"):
        assert c in ev
    asr = {r[1] for r in cur.execute("PRAGMA table_info(assertions)").fetchall()}
    for c in ("extract_id", "assertion_hash", "nivel_inferencia"):
        assert c in asr
    pr = {r[1] for r in cur.execute("PRAGMA table_info(problems)").fetchall()}
    for c in ("es_empresa_competidora", "normalized_text", "normalized_hash",
              "solucion_existente_mencionada", "necesidad_software_inferida"):
        assert c in pr
    rr = {r[1] for r in cur.execute("PRAGMA table_info(research_runs)").fetchall()}
    assert "partial_reason" in rr
    con.close()
def test_old_and_new_evidence_indexes_coexist(alembic_config, sqlite_path):
    command.upgrade(alembic_config, "0006")
    con = sqlite3.connect(sqlite_path)
    idx = {r[1] for r in con.execute("PRAGMA index_list(evidence)").fetchall()}
    assert "ix_evidence_unique" in idx
    assert "ix_evidence_cita_unique" in idx
    con.close()
def test_assertions_idem_index_created(alembic_config, sqlite_path):
    command.upgrade(alembic_config, "0006")
    con = sqlite3.connect(sqlite_path)
    idx = {r[1] for r in con.execute("PRAGMA index_list(assertions)").fetchall()}
    assert "ix_assertions_idem_unique" in idx
    con.close()
def test_evidence_fks_preserved(alembic_config, sqlite_path):
    command.upgrade(alembic_config, "0006")
    con = sqlite3.connect(sqlite_path)
    fks = con.execute("PRAGMA foreign_key_list(evidence)").fetchall()
    assert {r[2] for r in fks} == {"extracts", "sources", "assertions"}
    con.close()
def test_foreign_key_check_empty_on_clean_db(alembic_config, sqlite_path):
    command.upgrade(alembic_config, "0006")
    con = sqlite3.connect(sqlite_path)
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.close()
def test_downgrade_returns_to_0005(alembic_config, sqlite_path):
    command.upgrade(alembic_config, "head")
    command.downgrade(
        alembic_config, "0005_add_research_run_sources_and_extract_status",
    )
    con = sqlite3.connect(sqlite_path)
    ev_cols = {r[1] for r in con.execute("PRAGMA table_info(evidence)").fetchall()}
    assert "cita_hash" not in ev_cols
    assert "clasificacion_evidencia" not in ev_cols
    assert "limitaciones_evidencia" not in ev_cols
    assert "posicion_inicio" not in ev_cols
    assert "posicion_fin" not in ev_cols
    asr_cols = {r[1] for r in con.execute("PRAGMA table_info(assertions)").fetchall()}
    assert "extract_id" not in asr_cols
    assert "assertion_hash" not in asr_cols
    assert "nivel_inferencia" not in asr_cols
    pr_cols = {r[1] for r in con.execute("PRAGMA table_info(problems)").fetchall()}
    assert "es_empresa_competidora" not in pr_cols
    assert "normalized_text" not in pr_cols
    assert "normalized_hash" not in pr_cols
    assert "solucion_existente_mencionada" not in pr_cols
    assert "necesidad_software_inferida" not in pr_cols
    rr_cols = {r[1] for r in con.execute("PRAGMA table_info(research_runs)").fetchall()}
    assert "partial_reason" not in rr_cols
    ev_idx = {r[1] for r in con.execute("PRAGMA index_list(evidence)").fetchall()}
    assert "ix_evidence_cita_unique" not in ev_idx
    asr_idx = {r[1] for r in con.execute("PRAGMA index_list(assertions)").fetchall()}
    assert "ix_assertions_idem_unique" not in asr_idx
    pr_idx = {r[1] for r in con.execute("PRAGMA index_list(problems)").fetchall()}
    assert "ix_problems_normalized_hash" not in pr_idx
    assert "ix_evidence_unique" in ev_idx
    assert "ix_evidence_assertion_id" in ev_idx
    assert "ix_assertions_problem_id" in asr_idx
    assert "ix_problems_run_id" in pr_idx
    ev_fks = con.execute("PRAGMA foreign_key_list(evidence)").fetchall()
    assert {r[2] for r in ev_fks} == {"extracts", "sources", "assertions"}
    asr_fks = con.execute("PRAGMA foreign_key_list(assertions)").fetchall()
    assert {r[2] for r in asr_fks} == {"problems"}
    pr_fks = con.execute("PRAGMA foreign_key_list(problems)").fetchall()
    assert {r[2] for r in pr_fks} == {"research_runs"}
    version = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == "0005_add_research_run_sources_and_extract_status"
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.close()
def test_fk_check_catches_real_violation(alembic_config, engine, sqlite_path):
    command.upgrade(alembic_config, "0005_add_research_run_sources_and_extract_status")
    con = sqlite3.connect(sqlite_path)
    cols = {r[1] for r in con.execute("PRAGMA table_info(assertions)").fetchall()}
    required = {"problem_id", "text", "assertion_type", "confidence", "created_by"}
    assert required.issubset(cols), f"Faltan columnas en assertions: {required - cols}"
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute(
        "INSERT INTO assertions (problem_id, text, assertion_type, confidence, created_by, created_at) "
        "VALUES (999999, 'huerfana', 'hipotesis', 50, 'test', '2026-01-01 00:00:00')"
    )
    con.commit()
    orphan_id = con.execute(
        "SELECT id FROM assertions WHERE problem_id=999999"
    ).fetchone()[0]
    con.close()
    with engine.connect() as conn:
        alembic_config.attributes["connection"] = conn
        with pytest.raises(RuntimeError, match="foreign_key_check failed"):
            command.upgrade(alembic_config, "0006")
        assert alembic_config.attributes["_final_fk_state"] == 1
        cur = conn.connection.dbapi_connection.cursor()
        try:
            version = cur.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()[0]
            assert version == "0005_add_research_run_sources_and_extract_status"
            orphan = cur.execute(
                "SELECT id FROM assertions WHERE id=?", (orphan_id,)
            ).fetchone()
            assert orphan is not None
            ev_cols = {r[1] for r in cur.execute("PRAGMA table_info(evidence)").fetchall()}
            assert "cita_hash" not in ev_cols
        finally:
            cur.close()
def test_p5_full_ddl_rollback_on_fk_violation(alembic_config, engine, sqlite_path):
    command.upgrade(alembic_config, "0005_add_research_run_sources_and_extract_status")
    con = sqlite3.connect(sqlite_path)
    try:
        version_inicial = con.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        assert version_inicial == "0005_add_research_run_sources_and_extract_status"
        assert con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 0
        fk_list = con.execute("PRAGMA foreign_key_list(assertions)").fetchall()
        fk_problem = [
            r for r in fk_list
            if r[2] == "problems" and r[3] == "problem_id" and r[4] == "id"
        ]
        assert len(fk_problem) == 1, (
            f"FK assertions.problem_id -> problems no encontrada o ambigua: {fk_list}"
        )
        fkid_problem = fk_problem[0][0]
    finally:
        con.close()
    orphan_problem_id = 999999
    con_seed = sqlite3.connect(sqlite_path)
    try:
        con_seed.execute("PRAGMA foreign_keys=OFF")
        con_seed.execute(
            "INSERT INTO assertions "
            "(problem_id, text, assertion_type, confidence, created_by, created_at) "
            "VALUES (?, 'huerfana', 'hipotesis', 50, 'test', '2026-01-01 00:00:00')",
            (orphan_problem_id,),
        )
        con_seed.commit()
        orphan_id = con_seed.execute(
            "SELECT id FROM assertions WHERE problem_id=?",
            (orphan_problem_id,),
        ).fetchone()[0]
    finally:
        con_seed.close()
    with engine.connect() as conn:
        expected_dbapi_id = id(conn.connection.dbapi_connection)
        alembic_config.attributes["connection"] = conn
        with pytest.raises(RuntimeError, match="foreign_key_check failed"):
            command.upgrade(alembic_config, "0006")
        dbapi = conn.connection.dbapi_connection
        assert alembic_config.attributes.get("_dbapi_used_id") == expected_dbapi_id, (
            "env.py no uso la conexion inyectada: "
            f"_dbapi_used_id={alembic_config.attributes.get('_dbapi_used_id')!r} "
            f"vs id(conn.dbapi)={expected_dbapi_id!r}"
        )
        assert dbapi.in_transaction is False, (
            "DBAPI con transaccion abierta tras el rollback"
        )
        assert conn.in_transaction() is False, (
            "SQLAlchemy reporta transaccion abierta tras el rollback"
        )
        cur = dbapi.cursor()
        try:
            assert cur.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert alembic_config.attributes["_final_fk_state"] == 1
            prefix = "_alembic_tmp_"
            tmp = cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND substr(name, 1, ?) = ?",
                (len(prefix), prefix),
            ).fetchall()
            assert tmp == [], f"Tablas temporales huerfanas: {tmp}"
            for table, absent in {
                "evidence": {
                    "clasificacion_evidencia", "limitaciones_evidencia",
                    "posicion_inicio", "posicion_fin", "cita_hash",
                },
                "assertions": {"extract_id", "assertion_hash", "nivel_inferencia"},
                "problems": {
                    "es_empresa_competidora", "normalized_text",
                    "normalized_hash", "solucion_existente_mencionada",
                    "necesidad_software_inferida",
                },
                "research_runs": {"partial_reason"},
            }.items():
                cols = {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
                assert cols, f"Tabla {table} inexistente tras rollback"
                for c in absent:
                    assert c not in cols, f"Columna {c} presente en {table}"
            ev_idx = {r[1] for r in cur.execute("PRAGMA index_list(evidence)").fetchall()}
            assert {"ix_evidence_unique", "ix_evidence_assertion_id"} <= ev_idx
            assert "ix_evidence_cita_unique" not in ev_idx
            asr_idx = {r[1] for r in cur.execute("PRAGMA index_list(assertions)").fetchall()}
            assert "ix_assertions_problem_id" in asr_idx
            assert "ix_assertions_idem_unique" not in asr_idx
            pr_idx = {r[1] for r in cur.execute("PRAGMA index_list(problems)").fetchall()}
            assert "ix_problems_run_id" in pr_idx
            assert "ix_problems_normalized_hash" not in pr_idx
            version = cur.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()[0]
            assert version == "0005_add_research_run_sources_and_extract_status"
            orphan = cur.execute(
                "SELECT id FROM assertions WHERE id=?", (orphan_id,)
            ).fetchone()
            assert orphan is not None
            violations = cur.execute("PRAGMA foreign_key_check").fetchall()
            expected = ("assertions", orphan_id, "problems", fkid_problem)
            assert len(violations) == 1, (
                f"Se esperaba 1 violacion, encontradas: {violations}"
            )
            assert violations[0] == expected, (
                f"Violacion inesperada: {violations[0]!r} != {expected!r}"
            )
        finally:
            cur.close()
