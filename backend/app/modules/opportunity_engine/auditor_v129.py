"""Auditor SQLite v12.9 — RADAR LAB — Parte 1.

Funciones puras de la Parte 1:
  - _validate_spec_on_load
  - run_g14
  - traverse_alembic
  - compute_counters
  - normalize_type
"""
from __future__ import annotations

import math
import re
import sqlite3
from typing import Any


class SpecConstructionError(RuntimeError):
    """La spec es inconsistente y el auditor no debe ejecutarse."""


EXPECTED_VERSION = {
    "CURRENT": "0006",
    "BACKUP": "0005_add_research_run_sources_and_extract_status",
}

SQLITE_BUSY = 5
SQLITE_CONSTRAINT_UNIQUE = 2067
SQLITE_CONSTRAINT_FOREIGNKEY = 787
SQLITE_CONSTRAINT_NOTNULL = 1299
SQLITE_CONSTRAINT_CHECK = 275

# 24 índices/constraints únicos (21 origin='c' + 3 origin='u').
EXPECTED_INDEXES_SPEC = [
    {"table": "users", "name": "ix_users_email",
     "columns": ["email"], "unique": True, "partial": False,
     "kind": "unique_index", "verified_from": "0001_initial_users"},
    {"table": "sectors", "name": "ix_sectors_code",
     "columns": ["code"], "unique": True, "partial": False,
     "kind": "unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "sectors", "name": "ix_sectors_status",
     "columns": ["status"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "territories", "name": "ix_territories_code",
     "columns": ["code"], "unique": True, "partial": False,
     "kind": "unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "territories", "name": "ix_territories_level",
     "columns": ["level"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "territories", "name": "ix_territories_parent",
     "columns": ["parent_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "research_runs", "name": "ix_runs_user_status",
     "columns": ["user_id", "status"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "research_runs", "name": "ix_runs_sector_territory",
     "columns": ["sector_id", "territory_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0002_add_sectors_territories_research_runs"},
    {"table": "queries", "name": "ix_queries_run_id",
     "columns": ["research_run_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "queries", "name": "uq_query_run_text",
     "columns": ["research_run_id", "query_text"], "unique": True, "partial": False,
     "kind": "unique_constraint", "verified_from": "0004_add_reports_and_watchdog_fields"},
    {"table": "sources", "name": "ix_sources_normalized_url",
     "columns": ["normalized_url"], "unique": True, "partial": False,
     "kind": "unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "extracts", "name": "ix_extracts_source_id",
     "columns": ["source_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "extracts", "name": "uq_extracts_source_id",
     "columns": ["source_id"], "unique": True, "partial": False,
     "kind": "unique_constraint", "verified_from": "0005_add_research_run_sources_and_extract_status"},
    {"table": "problems", "name": "ix_problems_run_id",
     "columns": ["research_run_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "problems", "name": "ix_problems_normalized_hash",
     "columns": ["normalized_hash"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0006_add_analyzing_v1_fields_and_partial_reason"},
    {"table": "assertions", "name": "ix_assertions_problem_id",
     "columns": ["problem_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "assertions", "name": "ix_assertions_idem_unique",
     "columns": ["problem_id", "extract_id", "assertion_hash"],
     "unique": True, "partial": False, "kind": "unique_index",
     "verified_from": "0006_add_analyzing_v1_fields_and_partial_reason"},
    {"table": "evidence", "name": "ix_evidence_assertion_id",
     "columns": ["assertion_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "evidence", "name": "ix_evidence_unique",
     "columns": ["assertion_id", "source_id", "extract_id"],
     "unique": True, "partial": False, "kind": "unique_index",
     "verified_from": "0003_add_research_tables"},
    {"table": "evidence", "name": "ix_evidence_cita_unique",
     "columns": ["assertion_id", "cita_hash"], "unique": True, "partial": False,
     "kind": "unique_index", "verified_from": "0006_add_analyzing_v1_fields_and_partial_reason"},
    {"table": "opportunities", "name": "ix_opportunities_run_id",
     "columns": ["research_run_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0003_add_research_tables"},
    {"table": "reports", "name": "ix_reports_run_id",
     "columns": ["research_run_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0004_add_reports_and_watchdog_fields"},
    {"table": "research_run_sources", "name": "ix_run_sources_run_id",
     "columns": ["research_run_id"], "unique": False, "partial": False,
     "kind": "non_unique_index", "verified_from": "0005_add_research_run_sources_and_extract_status"},
    {"table": "research_run_sources", "name": "uq_run_source",
     "columns": ["research_run_id", "source_id"], "unique": True, "partial": False,
     "kind": "unique_constraint", "verified_from": "0005_add_research_run_sources_and_extract_status"},
]

# 18 FKs.
EXPECTED_FKS_SPEC = [
    {"from_table": "sectors", "from_col": "parent_id",
     "to_table": "sectors", "to_col": "id",
     "on_delete": "NO ACTION", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0002_add_sectors_territories_research_runs"},
    {"from_table": "territories", "from_col": "parent_id",
     "to_table": "territories", "to_col": "id",
     "on_delete": "NO ACTION", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0002_add_sectors_territories_research_runs"},
    {"from_table": "research_runs", "from_col": "user_id",
     "to_table": "users", "to_col": "id",
     "on_delete": "NO ACTION", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0002_add_sectors_territories_research_runs"},
    {"from_table": "research_runs", "from_col": "sector_id",
     "to_table": "sectors", "to_col": "id",
     "on_delete": "NO ACTION", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0002_add_sectors_territories_research_runs"},
    {"from_table": "research_runs", "from_col": "territory_id",
     "to_table": "territories", "to_col": "id",
     "on_delete": "NO ACTION", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0002_add_sectors_territories_research_runs"},
    {"from_table": "queries", "from_col": "research_run_id",
     "to_table": "research_runs", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "extracts", "from_col": "source_id",
     "to_table": "sources", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "problems", "from_col": "research_run_id",
     "to_table": "research_runs", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "assertions", "from_col": "problem_id",
     "to_table": "problems", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "assertions", "from_col": "extract_id",
     "to_table": "extracts", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE",
     "name": "fk_assertions_extract_id",
     "verified_from": "0006_add_analyzing_v1_fields_and_partial_reason"},
    {"from_table": "evidence", "from_col": "assertion_id",
     "to_table": "assertions", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "evidence", "from_col": "source_id",
     "to_table": "sources", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "evidence", "from_col": "extract_id",
     "to_table": "extracts", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "opportunities", "from_col": "research_run_id",
     "to_table": "research_runs", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "opportunities", "from_col": "problem_id",
     "to_table": "problems", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0003_add_research_tables"},
    {"from_table": "reports", "from_col": "research_run_id",
     "to_table": "research_runs", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0004_add_reports_and_watchdog_fields"},
    {"from_table": "research_run_sources", "from_col": "research_run_id",
     "to_table": "research_runs", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0005_add_research_run_sources_and_extract_status"},
    {"from_table": "research_run_sources", "from_col": "source_id",
     "to_table": "sources", "to_col": "id",
     "on_delete": "CASCADE", "on_update": "NO ACTION", "match": "NONE", "name": None,
     "verified_from": "0005_add_research_run_sources_and_extract_status"},
]

# 6 migraciones verificadas. 0001 confirmed tras PA22.
VERIFIED_MIGRATIONS = [
    {
        "file": "0001_initial_users.py", "position": 0,
        "revision_status": "confirmed", "revision": "0001_initial_users",
        "inferred_revision": None, "inference_source": None,
        "down_revision_status": "root_confirmed", "down_revision": None,
        "inferred_down_revision": None, "down_revision_source": "read_from_file",
        "verified_from": "content_of_0001_file",
    },
    {
        "file": "0002_add_sectors_territories_research_runs.py", "position": 1,
        "revision_status": "confirmed", "revision": "0002_add_sectors_territories_research_runs",
        "inferred_revision": None, "inference_source": None,
        "down_revision_status": "confirmed", "down_revision": "0001_initial_users",
        "inferred_down_revision": None, "down_revision_source": "read_from_file",
        "verified_from": "content_of_0002_file",
    },
    {
        "file": "0003_add_research_tables.py", "position": 2,
        "revision_status": "confirmed", "revision": "0003_add_research_tables",
        "inferred_revision": None, "inference_source": None,
        "down_revision_status": "confirmed",
        "down_revision": "0002_add_sectors_territories_research_runs",
        "inferred_down_revision": None, "down_revision_source": "read_from_file",
        "verified_from": "content_of_0003_file",
    },
    {
        "file": "0004_add_reports_and_watchdog_fields.py", "position": 3,
        "revision_status": "confirmed", "revision": "0004_add_reports_and_watchdog_fields",
        "inferred_revision": None, "inference_source": None,
        "down_revision_status": "confirmed", "down_revision": "0003_add_research_tables",
        "inferred_down_revision": None, "down_revision_source": "read_from_file",
        "verified_from": "content_of_0004_file",
    },
    {
        "file": "0005_add_research_run_sources_and_extract_status.py", "position": 4,
        "revision_status": "confirmed",
        "revision": "0005_add_research_run_sources_and_extract_status",
        "inferred_revision": None, "inference_source": None,
        "down_revision_status": "confirmed",
        "down_revision": "0004_add_reports_and_watchdog_fields",
        "inferred_down_revision": None,
        "down_revision_source": "asserted_by_user_read_from_file",
        "verified_from": "user_assertion_0005_not_read_literally_in_this_conversation",
    },
    {
        "file": "0006_add_analyzing_v1_fields_and_partial_reason.py", "position": 5,
        "revision_status": "confirmed",
        "revision": "0006",
        "inferred_revision": None, "inference_source": None,
        "down_revision_status": "confirmed",
        "down_revision": "0005_add_research_run_sources_and_extract_status",
        "inferred_down_revision": None,
        "down_revision_source": "asserted_by_user_read_from_file",
        "verified_from": "user_assertion_0006_not_read_literally_in_this_conversation",
    },
]


def _validate_spec_on_load():
    """CA-40: malformed entries abortan la carga con SpecConstructionError."""
    required = ["file", "revision_status", "down_revision_status", "verified_from"]
    for i, entry in enumerate(VERIFIED_MIGRATIONS):
        for f in required:
            if f not in entry:
                raise SpecConstructionError(
                    f"VERIFIED_MIGRATIONS[{i}] missing field '{f}'"
                )
        rs = entry["revision_status"]
        if rs not in ("confirmed", "inferred", "unknown"):
            raise SpecConstructionError(
                f"VERIFIED_MIGRATIONS[{i}] revision_status={rs!r} invalid"
            )
        if rs == "confirmed" and not entry.get("revision"):
            raise SpecConstructionError(
                f"VERIFIED_MIGRATIONS[{i}] confirmed but revision missing"
            )
        if rs != "confirmed" and not entry.get("inferred_revision"):
            raise SpecConstructionError(
                f"VERIFIED_MIGRATIONS[{i}] non-confirmed but inferred_revision missing"
            )
        drs = entry["down_revision_status"]
        if drs not in ("confirmed", "inferred", "unknown", "root_confirmed", "root_inferred"):
            raise SpecConstructionError(
                f"VERIFIED_MIGRATIONS[{i}] down_revision_status={drs!r} invalid"
            )
        if drs == "confirmed" and not entry.get("down_revision"):
            raise SpecConstructionError(
                f"VERIFIED_MIGRATIONS[{i}] confirmed down_revision missing"
            )
        if drs == "root_confirmed" and entry.get("down_revision") is not None:
            raise SpecConstructionError(
                f"VERIFIED_MIGRATIONS[{i}] root_confirmed but down_revision not None"
            )

    for i, ix in enumerate(EXPECTED_INDEXES_SPEC):
        for f in ("table", "name", "columns", "unique", "partial", "kind", "verified_from"):
            if f not in ix:
                raise SpecConstructionError(f"EXPECTED_INDEXES_SPEC[{i}] missing '{f}'")
        if ix["kind"] not in ("unique_index", "unique_constraint", "non_unique_index"):
            raise SpecConstructionError(f"EXPECTED_INDEXES_SPEC[{i}] invalid kind")

    for i, fk in enumerate(EXPECTED_FKS_SPEC):
        for f in ("from_table", "from_col", "to_table", "to_col",
                  "on_delete", "on_update", "match", "verified_from"):
            if f not in fk:
                raise SpecConstructionError(f"EXPECTED_FKS_SPEC[{i}] missing '{f}'")


_validate_spec_on_load()


def normalize_type(t):
    """Normaliza el tipo declarado de una columna para comparaciones."""
    return (t or "").upper().strip()


def run_g14():
    """Valida el grafo de la spec. Triggers T1, T2, T3, T4."""
    errors = []
    confirmed = [m for m in VERIFIED_MIGRATIONS if m["revision_status"] == "confirmed"]
    inferred = [m for m in VERIFIED_MIGRATIONS
                if m["revision_status"] in ("inferred", "unknown")]

    seen = {}
    for m in confirmed:
        rev = m["revision"]
        if rev in seen:
            errors.append({"trigger": "T1_duplicate_revision", "revision": rev,
                           "files": [seen[rev], m["file"]]})
        else:
            seen[rev] = m["file"]

    confirmed_revs = {m["revision"] for m in confirmed}
    inferred_revs = {m["inferred_revision"] for m in inferred
                     if m.get("inferred_revision")}

    for m in confirmed:
        if m["down_revision_status"] == "confirmed" and m.get("down_revision"):
            dr = m["down_revision"]
            if dr not in confirmed_revs and dr not in inferred_revs:
                errors.append({
                    "trigger": "T2_dangling_down_revision",
                    "entry_file": m["file"],
                    "down_revision": dr,
                    "reason": "no matching revision or inferred_revision in spec",
                })

    graph = {m["revision"]: m["down_revision"] for m in confirmed
             if m["down_revision_status"] == "confirmed" and m.get("down_revision")}
    for start in graph:
        seen_nodes = set()
        cur = start
        while cur in graph and cur not in seen_nodes:
            seen_nodes.add(cur)
            cur = graph[cur]
        if cur == start:
            errors.append({"trigger": "T3_cycle", "revision": start})

    for m in inferred:
        ir = m.get("inferred_revision")
        if ir and ir in confirmed_revs:
            other = next((x for x in confirmed if x["revision"] == ir), None)
            if other and other["file"] != m["file"]:
                errors.append({
                    "trigger": "T4_inferred_confirmed_collision",
                    "inferred_revision": ir,
                    "inferred_from": m["file"],
                    "confirmed_in": other["file"],
                })

    return {"spec_graph_valid": len(errors) == 0, "errors": errors,
            "ok": len(errors) == 0}


def traverse_alembic(conn: sqlite3.Connection, expected_version: str) -> dict:
    """Clasifica la versión de Alembic según CA-33.

    Prioridad por orden de detección. Nota I-09: alembic_broken_chain declarado
    pero no implementado. Nota DT-01: alembic_merge_revision detectado antes de
    recorrer los padres; un ciclo entre ellos no se detecta.

    Contrato de detail por sub_status:
      - alembic_read_error: {"error"}
      - alembic_version_empty: None
      - alembic_version_multi_row: {"rows"}
      - alembic_cycle: {"cycle_at"}
      - alembic_merge_revision: {"merge_node", "parents"}
      - spec_incomplete: {"incomplete_entries", "proof_type"}
      - spec_incomplete_dependency_unknown: {"unknown_entries", "uncertainty"}
      - spec_outdated: {"revisions_outside_spec"}
      - version_mismatch: {"current", "expected"}
      - OK_VERIFIED: None
    """
    cur = conn.cursor()
    try:
        rows = cur.execute("SELECT version_num FROM alembic_version").fetchall()
    except Exception as e:
        return {"canonical_status": "BLOCKED",
                "sub_status": "alembic_read_error",
                "detail": {"error": str(e)}}

    if len(rows) == 0:
        return {"canonical_status": "BLOCKED",
                "sub_status": "alembic_version_empty", "detail": None}
    if len(rows) > 1:
        return {"canonical_status": "BLOCKED",
                "sub_status": "alembic_version_multi_row",
                "detail": {"rows": [r[0] for r in rows]}}

    current = rows[0][0]

    down_map = {m["revision"]: m["down_revision"] for m in VERIFIED_MIGRATIONS
                if m["revision_status"] == "confirmed"}
    inferred_map = {m["inferred_revision"]: m["inferred_down_revision"]
                    for m in VERIFIED_MIGRATIONS
                    if m["revision_status"] != "confirmed"
                    and m.get("inferred_revision")}

    chain = []
    visited = set()
    stack = [current]
    while stack:
        rev = stack.pop()
        if rev in visited:
            return {"canonical_status": "BLOCKED",
                    "sub_status": "alembic_cycle",
                    "detail": {"cycle_at": rev}}
        visited.add(rev)
        chain.append(rev)
        if rev in down_map:
            parent = down_map[rev]
        elif rev in inferred_map:
            parent = inferred_map[rev]
        else:
            parent = None
        if isinstance(parent, tuple):
            return {"canonical_status": "BLOCKED",
                    "sub_status": "alembic_merge_revision",
                    "detail": {"merge_node": rev, "parents": list(parent)}}
        if parent:
            stack.append(parent)

    incomplete_entries = []
    unknown_entries = []
    for m in VERIFIED_MIGRATIONS:
        rs = m["revision_status"]
        if rs == "confirmed":
            is_fully = m["down_revision_status"] in ("confirmed", "root_confirmed")
            if m["revision"] in chain and not is_fully:
                incomplete_entries.append(m)
        else:
            unknown_entries.append(m)

    if incomplete_entries:
        return {"canonical_status": "BLOCKED",
                "sub_status": "spec_incomplete",
                "detail": {"incomplete_entries": incomplete_entries,
                           "proof_type": "direct"}}
    if unknown_entries:
        return {"canonical_status": "BLOCKED",
                "sub_status": "spec_incomplete_dependency_unknown",
                "detail": {"unknown_entries": unknown_entries,
                           "uncertainty": "revision_id_unknown"}}

    verified_revs = {m["revision"] for m in VERIFIED_MIGRATIONS
                     if m["revision_status"] == "confirmed"}
    outside = [r for r in chain if r not in verified_revs]
    if outside:
        return {"canonical_status": "BLOCKED",
                "sub_status": "spec_outdated",
                "detail": {"revisions_outside_spec": outside}}

    if current != expected_version:
        return {"canonical_status": "MISMATCH",
                "sub_status": "version_mismatch",
                "detail": {"current": current, "expected": expected_version}}

    return {"canonical_status": "OK_VERIFIED", "sub_status": None, "detail": None}


def compute_counters(results: list[dict]) -> dict:
    """Agrega contadores por canonical_status. Componente aislado (C14, I-03)."""
    counters = {
        "verified_count": 0,
        "unverified_count": 0,
        "pending_count": 0,
        "blocked_count": 0,
        "mismatch_count": 0,
    }
    for r in results:
        c = r["canonical_status"]
        if c == "OK_VERIFIED":
            counters["verified_count"] += 1
        elif c == "OK_UNVERIFIED":
            counters["unverified_count"] += 1
        elif c == "PENDING":
            counters["pending_count"] += 1
        elif c == "BLOCKED":
            counters["blocked_count"] += 1
        elif c == "MISMATCH":
            counters["mismatch_count"] += 1
    return counters