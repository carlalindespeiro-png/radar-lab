"""Tests del auditor v12.9 — RADAR LAB — Parte 1.

40 tests:
  - A1–A8:     spec construction (CA-40, PA32)
  - B1–B12:    G14 spec graph T1–T4 (CA-41, T3-dec)
  - C1–C17:    traversal Alembic (CA-31, CA-33, CA-35, CA-38)
  - T-R1:      merge revision en mitad de cadena
  - T-R2a:     ciclo detectado antes que merge
  - T-R2b:     merge detectado antes que ciclo (padres no recorridos)

Todos los tests usan tmp_path (SQLite temporal).
Ninguno toca backend/radar_lab.db.

Incidencias documentadas: I-03, I-04, I-05, I-06, I-09, I-10.
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.modules.opportunity_engine import auditor_v129 as A


def _mk_conn(tmp_path: Path, version_rows=None, extra_sql: str = ""):
    p = tmp_path / f"test_{uuid.uuid4().hex}.db"
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num TEXT)")
    for v in (version_rows or []):
        conn.execute("INSERT INTO alembic_version VALUES (?)", (v,))
    if extra_sql:
        conn.executescript(extra_sql)
    conn.commit()
    return conn


@contextmanager
def _temp_conn(tmp_path: Path, version_rows=None, extra_sql: str = ""):
    conn = _mk_conn(tmp_path, version_rows, extra_sql)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ===========================================================================
# GRUPO A — Spec construction (8 tests)
# ===========================================================================

def test_spec_construction_ok():
    A._validate_spec_on_load()


def test_spec_missing_file_field(monkeypatch):
    bad = [dict(A.VERIFIED_MIGRATIONS[0])]
    del bad[0]["file"]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", bad)
    with pytest.raises(A.SpecConstructionError, match="missing field 'file'"):
        A._validate_spec_on_load()


def test_spec_missing_revision_status(monkeypatch):
    bad = [dict(A.VERIFIED_MIGRATIONS[1])]
    del bad[0]["revision_status"]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", bad)
    with pytest.raises(A.SpecConstructionError, match="missing field 'revision_status'"):
        A._validate_spec_on_load()


def test_spec_invalid_revision_status(monkeypatch):
    bad = [dict(A.VERIFIED_MIGRATIONS[1], revision_status="nonsense")]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", bad)
    with pytest.raises(A.SpecConstructionError, match="revision_status"):
        A._validate_spec_on_load()


def test_spec_confirmed_but_no_revision(monkeypatch):
    bad = [dict(A.VERIFIED_MIGRATIONS[1], revision=None)]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", bad)
    with pytest.raises(A.SpecConstructionError, match="confirmed but revision missing"):
        A._validate_spec_on_load()


def test_spec_unknown_requires_inferred_revision(monkeypatch):
    bad = [{"file": "x.py", "revision_status": "unknown", "revision": None,
            "inferred_revision": None, "inference_source": None,
            "down_revision_status": "unknown", "down_revision": None,
            "inferred_down_revision": None, "down_revision_source": None,
            "verified_from": None}]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", bad)
    with pytest.raises(A.SpecConstructionError, match="inferred_revision missing"):
        A._validate_spec_on_load()


def test_spec_root_confirmed_with_parent(monkeypatch):
    bad = [dict(A.VERIFIED_MIGRATIONS[1], down_revision_status="root_confirmed")]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", bad)
    with pytest.raises(A.SpecConstructionError, match="root_confirmed"):
        A._validate_spec_on_load()


def test_spec_no_t0_trigger_exists():
    g14 = A.run_g14()
    triggers = [e.get("trigger") for e in g14["errors"]]
    assert "T0_malformed_entry" not in triggers


# ===========================================================================
# GRUPO B — G14 Spec Graph (12 tests)
# ===========================================================================

def test_g14_clean_spec():
    g14 = A.run_g14()
    assert g14["ok"] is True
    assert g14["errors"] == []
    assert g14["spec_graph_valid"] is True


def test_g14_t1_duplicate_revision(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base.append(dict(base[2]))
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    t1 = [e for e in g14["errors"] if e["trigger"] == "T1_duplicate_revision"]
    assert len(t1) == 1
    assert t1[0]["revision"] == base[2]["revision"]


def test_g14_t2_dangling_down_revision(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["down_revision"] = "NOT_A_REAL_REVISION"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    t2 = [e for e in g14["errors"] if e["trigger"] == "T2_dangling_down_revision"]
    assert len(t2) == 1
    assert t2[0]["down_revision"] == "NOT_A_REAL_REVISION"
    assert t2[0]["entry_file"] == base[1]["file"]


def test_g14_t3_cycle(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS[:3]]
    base[0].update(revision="R1", revision_status="confirmed",
                   inferred_revision=None,
                   down_revision_status="confirmed", down_revision="R2")
    base[1].update(revision="R2", revision_status="confirmed",
                   inferred_revision=None,
                   down_revision_status="confirmed", down_revision="R1")
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    t3_errors = [e for e in g14["errors"] if e["trigger"] == "T3_cycle"]
    assert len(t3_errors) == 2
    assert {e["revision"] for e in t3_errors} == {"R1", "R2"}


def test_g14_t4_inferred_confirmed_collision(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[0]["revision_status"] = "inferred"
    base[0]["inferred_revision"] = base[1]["revision"]
    base[0]["revision"] = None
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    t4 = [e for e in g14["errors"] if e["trigger"] == "T4_inferred_confirmed_collision"]
    assert len(t4) == 1
    assert t4[0]["inferred_revision"] == base[1]["revision"]
    assert t4[0]["inferred_from"] == base[0]["file"]
    assert t4[0]["confirmed_in"] == base[1]["file"]


def test_g14_multi_child_valid(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[2]["down_revision"] = base[1]["down_revision"]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    assert g14["ok"] is True
    assert not any(e["trigger"] == "T2_dangling_down_revision" for e in g14["errors"])


def test_g14_root_inferred_ok(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["down_revision_status"] = "root_inferred"
    base[1]["down_revision"] = None
    base[1]["inferred_down_revision"] = None
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    assert not any(e["trigger"] == "T2_dangling_down_revision" for e in g14["errors"])


def test_g14_down_revision_unknown_ok(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["down_revision_status"] = "unknown"
    base[1]["down_revision"] = None
    base[1]["inferred_down_revision"] = None
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    assert g14["ok"] is True
    assert not any(e["trigger"] == "T2_dangling_down_revision" for e in g14["errors"])


def test_g14_multiple_errors_reported(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["down_revision"] = "X"
    base.append(dict(base[2]))
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    triggers = [e["trigger"] for e in g14["errors"]]
    assert "T1_duplicate_revision" in triggers
    assert "T2_dangling_down_revision" in triggers
    assert len(g14["errors"]) >= 2


def test_g14_all_triggers_independent(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base.append(dict(base[3]))
    base[1]["down_revision"] = "MISSING"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    t1 = [e for e in g14["errors"] if e["trigger"] == "T1_duplicate_revision"]
    t2 = [e for e in g14["errors"] if e["trigger"] == "T2_dangling_down_revision"]
    assert len(t1) == 1
    assert len(t2) == 1
    assert t1[0]["revision"] == base[3]["revision"]
    assert t2[0]["down_revision"] == "MISSING"


def test_g14_accepts_declared_inferred_down_revision(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[0]["revision_status"] = "unknown"
    base[0]["revision"] = None
    base[0]["inferred_revision"] = "0001_initial_users"
    base[0]["inference_source"] = "test_construction"
    base[0]["down_revision_status"] = "unknown"
    base[0]["down_revision"] = None
    base[0]["inferred_down_revision"] = None
    base[0]["down_revision_source"] = None
    base[0]["verified_from"] = None

    e1, e2 = base[0], base[1]
    assert e1["revision_status"] == "unknown"
    assert e1["revision"] is None
    assert e1["inferred_revision"] == "0001_initial_users"
    assert e2["down_revision"] == "0001_initial_users"
    confirmed_revs = {m["revision"] for m in base
                      if m["revision_status"] == "confirmed"}
    assert "0001_initial_users" not in confirmed_revs
    assert e2["down_revision"] == e1["inferred_revision"]

    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    triggers = [e["trigger"] for e in g14["errors"]]
    assert "T1_duplicate_revision" not in triggers
    assert "T2_dangling_down_revision" not in triggers
    assert "T3_cycle" not in triggers
    assert "T4_inferred_confirmed_collision" not in triggers
    assert g14["spec_graph_valid"] is True
    assert g14["errors"] == []


def test_g14_t2_ignores_inferred_down_revision_status(monkeypatch):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[2]["down_revision_status"] = "inferred"
    base[2]["down_revision"] = None
    base[2]["inferred_down_revision"] = "DOES_NOT_EXIST"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    g14 = A.run_g14()
    assert not any(e["trigger"] == "T2_dangling_down_revision" for e in g14["errors"])


# ===========================================================================
# GRUPO C — Traversal Alembic (17 tests)
# ===========================================================================

def test_traverse_version_empty(tmp_path):
    with _temp_conn(tmp_path, []) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "BLOCKED"
        assert r["sub_status"] == "alembic_version_empty"


def test_traverse_version_multi_row(tmp_path):
    with _temp_conn(tmp_path, ["A", "B"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "BLOCKED"
        assert r["sub_status"] == "alembic_version_multi_row"


def test_traverse_current_exact_match_verified(tmp_path):
    with _temp_conn(tmp_path, ["0006"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "OK_VERIFIED"
        assert r["sub_status"] is None


def test_traverse_backup_exact_match_verified(tmp_path):
    with _temp_conn(tmp_path,
                    ["0005_add_research_run_sources_and_extract_status"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["BACKUP"])
        assert r["canonical_status"] == "OK_VERIFIED"
        assert r["sub_status"] is None


def test_traverse_version_mismatch_fires(tmp_path):
    with _temp_conn(tmp_path,
                    ["0005_add_research_run_sources_and_extract_status"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "MISMATCH"
        assert r["sub_status"] == "version_mismatch"


def test_traverse_all_verified_ok(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["0006"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "OK_VERIFIED"
        assert r["sub_status"] is None


def test_traverse_spec_outdated(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["0007_add_evidence_unique_removal"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "BLOCKED"
        assert r["sub_status"] == "spec_outdated"
        assert r["detail"]["revisions_outside_spec"] == ["0007_add_evidence_unique_removal"]


def test_traverse_version_mismatch(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path,
                    ["0005_add_research_run_sources_and_extract_status"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["canonical_status"] == "MISMATCH"
        assert r["sub_status"] == "version_mismatch"


def test_traverse_cycle_detected(monkeypatch, tmp_path):
    base = [
        dict(file="r1.py", position=0, revision_status="confirmed",
             revision="R1", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="R2",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="r2.py", position=1, revision_status="confirmed",
             revision="R2", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="R1",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
    ]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["R1"]) as conn:
        r = A.traverse_alembic(conn, "R1")
        assert r["canonical_status"] == "BLOCKED"
        assert r["sub_status"] == "alembic_cycle"


def test_traverse_read_error(tmp_path):
    p = tmp_path / f"noread_{uuid.uuid4().hex}.db"
    conn = sqlite3.connect(p)
    try:
        r = A.traverse_alembic(conn, "0006")
        assert r["canonical_status"] == "BLOCKED"
        assert r["sub_status"] == "alembic_read_error"
        assert r["sub_status"] != "alembic_version_empty"
    finally:
        conn.close()


def test_traverse_version_empty_returns_structural_state(tmp_path):
    with _temp_conn(tmp_path, []) as conn:
        r = A.traverse_alembic(conn, "0006")
        assert r["sub_status"] == "alembic_version_empty"
        assert r["sub_status"] != "spec_inconsistent"


def test_traverse_spec_incomplete_dependency_unknown_detail(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["revision_status"] = "unknown"
    base[1]["revision"] = None
    base[1]["inferred_revision"] = "0002_add_sectors_territories_research_runs"
    base[1]["inference_source"] = "test_construction"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["0006"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["sub_status"] == "spec_incomplete_dependency_unknown"
        detail = r["detail"]
        assert "unknown_entries" in detail
        assert detail["uncertainty"] == "revision_id_unknown"
        for e in detail["unknown_entries"]:
            assert "file" in e
            assert "revision_status" in e
            assert "inferred_revision" in e


def test_traverse_spec_incomplete_direct(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[4]["down_revision_status"] = "inferred"
    base[4]["down_revision"] = None
    base[4]["inferred_down_revision"] = "0004_add_reports_and_watchdog_fields"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["0006"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["sub_status"] == "spec_incomplete"
        assert "incomplete_entries" in r["detail"]
        assert r["detail"]["proof_type"] == "direct"


def test_traverse_unknown_entries_not_duplicated(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["revision_status"] = "unknown"
    base[1]["revision"] = None
    base[1]["inferred_revision"] = "0002_add_sectors_territories_research_runs"
    base[1]["inference_source"] = "test_construction"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["0006"]) as conn:
        t_current = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
    with _temp_conn(tmp_path,
                    ["0005_add_research_run_sources_and_extract_status"]) as conn:
        t_backup = A.traverse_alembic(conn, A.EXPECTED_VERSION["BACKUP"])

    assert t_current["sub_status"] == "spec_incomplete_dependency_unknown"
    assert len(t_current["detail"]["unknown_entries"]) == 1
    assert t_backup["sub_status"] == "spec_incomplete_dependency_unknown"
    assert len(t_backup["detail"]["unknown_entries"]) == 1

    def _entity(label, t):
        return {
            "entity_kind": "version_check",
            "entity_label": label,
            "canonical_status": t["canonical_status"],
            "sub_status": t["sub_status"],
            "detail": t.get("detail"),
        }
    results = [_entity("CURRENT", t_current), _entity("BACKUP", t_backup)]
    counters = A.compute_counters(results)
    assert len(results) == 2
    assert counters["blocked_count"] == 2
    assert counters["blocked_count"] != 4


def test_traverse_priority_incomplete_over_unknown(monkeypatch, tmp_path):
    base = [dict(m) for m in A.VERIFIED_MIGRATIONS]
    base[1]["revision_status"] = "unknown"
    base[1]["revision"] = None
    base[1]["inferred_revision"] = "0002_add_sectors_territories_research_runs"
    base[1]["inference_source"] = "test_construction"
    base[4]["down_revision_status"] = "inferred"
    base[4]["down_revision"] = None
    base[4]["inferred_down_revision"] = "0004_add_reports_and_watchdog_fields"
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    with _temp_conn(tmp_path, ["0006"]) as conn:
        r = A.traverse_alembic(conn, A.EXPECTED_VERSION["CURRENT"])
        assert r["sub_status"] == "spec_incomplete"
        assert r["sub_status"] != "spec_incomplete_dependency_unknown"


def test_traverse_cycle_precedes_unknown(monkeypatch, tmp_path):
    base_common = [
        dict(file="r1.py", position=0, revision_status="confirmed",
             revision="R1", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="R2",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="r2.py", position=1, revision_status="confirmed",
             revision="R2", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="R1",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="unknown.py", position=2, revision_status="unknown",
             revision=None, inferred_revision="R1", inference_source="test",
             down_revision_status="unknown", down_revision=None,
             inferred_down_revision=None, down_revision_source=None,
             verified_from=None),
    ]
    down_map = {m["revision"]: m["down_revision"] for m in base_common
                if m["revision_status"] == "confirmed"}
    assert down_map["R1"] == "R2" and down_map["R2"] == "R1"

    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base_common)
    with _temp_conn(tmp_path, ["R1"]) as conn:
        r_a = A.traverse_alembic(conn, "R1")
    assert r_a["canonical_status"] == "BLOCKED"
    assert r_a["sub_status"] == "alembic_cycle"
    assert r_a["sub_status"] != "spec_incomplete_dependency_unknown"

    base_broken = [dict(m) for m in base_common]
    base_broken[1]["down_revision_status"] = "root_confirmed"
    base_broken[1]["down_revision"] = None
    down_map_b = {m["revision"]: m["down_revision"] for m in base_broken
                  if m["revision_status"] == "confirmed"}
    assert down_map_b["R1"] == "R2" and down_map_b["R2"] is None
    assert any(m["revision_status"] == "unknown"
               and m["inferred_revision"] == "R1" for m in base_broken)

    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base_broken)
    with _temp_conn(tmp_path, ["R1"]) as conn:
        r_b = A.traverse_alembic(conn, "R1")
    assert r_b["canonical_status"] == "BLOCKED"
    assert r_b["sub_status"] == "spec_incomplete_dependency_unknown"
    assert len(r_b["detail"]["unknown_entries"]) == 1
    assert r_a["sub_status"] != r_b["sub_status"]


def test_traverse_merge_revision(monkeypatch, tmp_path):
    base = [
        dict(file="r1.py", position=0, revision_status="confirmed",
             revision="R1", inferred_revision=None, inference_source=None,
             down_revision_status="root_confirmed", down_revision=None,
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="r2.py", position=1, revision_status="confirmed",
             revision="R2", inferred_revision=None, inference_source=None,
             down_revision_status="root_confirmed", down_revision=None,
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="merge_node.py", position=2, revision_status="confirmed",
             revision="merge_node", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision=("R1", "R2"),
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
    ]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)
    merge_entries = [m for m in base
                     if m["revision_status"] == "confirmed"
                     and isinstance(m.get("down_revision"), tuple)]
    assert len(merge_entries) == 1
    assert merge_entries[0]["revision"] == "merge_node"

    with _temp_conn(tmp_path, ["merge_node"]) as conn:
        r = A.traverse_alembic(conn, "merge_node")
    assert r["canonical_status"] == "BLOCKED"
    assert r["sub_status"] == "alembic_merge_revision"


# ===========================================================================
# T-R1, T-R2a, T-R2b
# ===========================================================================

def test_traverse_merge_in_middle_of_chain(monkeypatch, tmp_path):
    base = [
        dict(file="r1.py", position=0, revision_status="confirmed",
             revision="R1", inferred_revision=None, inference_source=None,
             down_revision_status="root_confirmed", down_revision=None,
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="r2.py", position=1, revision_status="confirmed",
             revision="R2", inferred_revision=None, inference_source=None,
             down_revision_status="root_confirmed", down_revision=None,
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="merge_node.py", position=2, revision_status="confirmed",
             revision="merge_node", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision=("R1", "R2"),
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="r3.py", position=3, revision_status="confirmed",
             revision="R3", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="merge_node",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
    ]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)

    with _temp_conn(tmp_path, ["R3"]) as conn:
        r = A.traverse_alembic(conn, "R3")

    assert r["canonical_status"] == "BLOCKED"
    assert r["sub_status"] == "alembic_merge_revision"
    assert r["detail"]["merge_node"] == "merge_node"
    assert r["detail"]["parents"] == ["R1", "R2"]


def test_traverse_cycle_precedes_merge(monkeypatch, tmp_path):
    base = [
        dict(file="cycle_a.py", position=0, revision_status="confirmed",
             revision="cycle_a", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="cycle_b",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="cycle_b.py", position=1, revision_status="confirmed",
             revision="cycle_b", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="cycle_a",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="merge_node.py", position=2, revision_status="confirmed",
             revision="merge_node", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision=("cycle_a", "cycle_b"),
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
    ]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)

    with _temp_conn(tmp_path, ["cycle_a"]) as conn:
        r = A.traverse_alembic(conn, "cycle_a")

    assert r["canonical_status"] == "BLOCKED"
    assert r["sub_status"] == "alembic_cycle"


def test_traverse_merge_precedes_cycle(monkeypatch, tmp_path):
    base = [
        dict(file="cycle_a.py", position=0, revision_status="confirmed",
             revision="cycle_a", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="cycle_b",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="cycle_b.py", position=1, revision_status="confirmed",
             revision="cycle_b", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision="cycle_a",
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
        dict(file="merge_node.py", position=2, revision_status="confirmed",
             revision="merge_node", inferred_revision=None, inference_source=None,
             down_revision_status="confirmed", down_revision=("cycle_a", "cycle_b"),
             inferred_down_revision=None, down_revision_source="x",
             verified_from="x"),
    ]
    monkeypatch.setattr(A, "VERIFIED_MIGRATIONS", base)

    with _temp_conn(tmp_path, ["merge_node"]) as conn:
        r = A.traverse_alembic(conn, "merge_node")

    assert r["canonical_status"] == "BLOCKED"
    assert r["sub_status"] == "alembic_merge_revision"
    assert r["detail"]["merge_node"] == "merge_node"