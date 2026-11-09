"""Tests de los contratos Pydantic de RADAR LAB.

33 tests:
  - A1–A6:   AnalyzeInput (6)
  - B1–B5:   EvidenceContract (5)
  - C1–C7:   Candidate (7)
  - D1–D9:   AnalyzeResult (9)
  - E1–E6:   PersistResult (6)

Todos los tests usan Pydantic directamente. Sin BD.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.modules.opportunity_engine.contracts import (
    AnalyzeInput,
    AnalyzeResult,
    Candidate,
    EvidenceContract,
    PersistResult,
)


VALID_HASH = "a" * 64  # SHA-256 hex ficticio para tests


def _valid_evidence() -> dict:
    return {
        "cita_literal": "los administradores pierden 5 horas semanales",
        "clasificacion_evidencia": "dato_presentado_como_hecho",
        "posicion_inicio": 0,
        "posicion_fin": 40,
        "limitaciones_evidencia": "sin cuantificación económica",
        "cita_hash": VALID_HASH,
    }


def _valid_candidate() -> dict:
    return {
        "interpretacion_problema": "Pérdida de tiempo en coordinación",
        "normalized_text": "perdida de tiempo en coordinacion",
        "normalized_hash": VALID_HASH,
        "nivel_inferencia": "inferencia_directa",
        "necesidad_software_inferida": True,
        "es_empresa_competidora": False,
        "solucion_existente_mencionada": "",
        "confidence_inicial": 60,
        "assertion_hash": VALID_HASH,
        "evidencias": [_valid_evidence()],
    }


def _valid_analyze_input() -> dict:
    return {
        "text": "texto de prueba",
        "source_id": 1,
        "extract_id": 1,
        "research_run_id": 1,
        "url": "https://example.com/a",
        "titulo": "Artículo",
        "tipo_fuente_previo": "foro",
    }


def _valid_analyze_result() -> dict:
    return {
        "source_id": 1,
        "extract_id": 1,
        "research_run_id": 1,
        "url": "https://example.com/a",
        "titulo": "Artículo",
        "analisis_posible": True,
        "tipo_fuente": "foro",
        "motivo_rechazo": None,
        "candidatos": [_valid_candidate()],
        "rechazos": [],
        "presupuesto_agotado": False,
        "bloques_procesados": 3,
        "bloques_totales": 3,
    }


def _valid_persist_result() -> dict:
    return {
        "research_run_id": 1,
        "extract_id": 1,
        "exito": True,
        "problems_creados": 1,
        "assertions_creadas": 1,
        "evidence_creadas": 1,
        "status_final": "analyzed_pending_corroboration",
    }


# ===========================================================================
# GRUPO A — AnalyzeInput (6 tests)
# ===========================================================================

def test_a1_analyze_input_valid():
    m = AnalyzeInput(**_valid_analyze_input())
    assert m.source_id == 1


def test_a2_analyze_input_empty_text():
    d = _valid_analyze_input()
    d["text"] = ""
    with pytest.raises(ValidationError):
        AnalyzeInput(**d)


def test_a3_analyze_input_missing_source_id():
    d = _valid_analyze_input()
    del d["source_id"]
    with pytest.raises(ValidationError):
        AnalyzeInput(**d)


def test_a4_analyze_input_missing_extract_id():
    d = _valid_analyze_input()
    del d["extract_id"]
    with pytest.raises(ValidationError):
        AnalyzeInput(**d)


def test_a5_analyze_input_missing_research_run_id():
    d = _valid_analyze_input()
    del d["research_run_id"]
    with pytest.raises(ValidationError):
        AnalyzeInput(**d)


def test_a6_analyze_input_invalid_tipo_fuente_previo():
    d = _valid_analyze_input()
    d["tipo_fuente_previo"] = "inventado"
    with pytest.raises(ValidationError):
        AnalyzeInput(**d)


# ===========================================================================
# GRUPO B — EvidenceContract (5 tests)
# ===========================================================================

def test_b1_evidence_valid_without_positions():
    d = _valid_evidence()
    d["posicion_inicio"] = None
    d["posicion_fin"] = None
    m = EvidenceContract(**d)
    assert m.posicion_inicio is None


def test_b2_evidence_invalid_cita_hash():
    d = _valid_evidence()
    d["cita_hash"] = "no-es-hex"
    with pytest.raises(ValidationError):
        EvidenceContract(**d)


def test_b3_evidence_invalid_positions_order():
    d = _valid_evidence()
    d["posicion_inicio"] = 40
    d["posicion_fin"] = 10
    with pytest.raises(ValidationError):
        EvidenceContract(**d)


def test_b4_evidence_limitaciones_too_long():
    d = _valid_evidence()
    d["limitaciones_evidencia"] = "x" * 301
    with pytest.raises(ValidationError):
        EvidenceContract(**d)


def test_b5_evidence_empty_cita_literal():
    d = _valid_evidence()
    d["cita_literal"] = ""
    with pytest.raises(ValidationError):
        EvidenceContract(**d)


# ===========================================================================
# GRUPO C — Candidate (7 tests)
# ===========================================================================

def test_c1_candidate_valid():
    m = Candidate(**_valid_candidate())
    assert m.confidence_inicial == 60


def test_c2_candidate_no_evidence():
    d = _valid_candidate()
    d["evidencias"] = []
    with pytest.raises(ValidationError):
        Candidate(**d)


def test_c3_candidate_confidence_too_high():
    d = _valid_candidate()
    d["confidence_inicial"] = 101
    with pytest.raises(ValidationError):
        Candidate(**d)


def test_c4_candidate_confidence_negative():
    d = _valid_candidate()
    d["confidence_inicial"] = -1
    with pytest.raises(ValidationError):
        Candidate(**d)


def test_c5_candidate_invalid_normalized_hash():
    d = _valid_candidate()
    d["normalized_hash"] = "zzz"
    with pytest.raises(ValidationError):
        Candidate(**d)


def test_c6_candidate_invalid_nivel_inferencia():
    d = _valid_candidate()
    d["nivel_inferencia"] = "nonsense"
    with pytest.raises(ValidationError):
        Candidate(**d)


def test_c7_candidate_solucion_none():
    d = _valid_candidate()
    d["solucion_existente_mencionada"] = None
    m = Candidate(**d)
    assert m.solucion_existente_mencionada is None


# ===========================================================================
# GRUPO D — AnalyzeResult (9 tests)
# ===========================================================================

def test_d1_analyze_result_valid_with_candidates():
    m = AnalyzeResult(**_valid_analyze_result())
    assert len(m.candidatos) == 1


def test_d2_analyze_result_possible_no_candidates():
    d = _valid_analyze_result()
    d["candidatos"] = []
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


def test_d3_analyze_result_not_possible_with_candidates():
    d = _valid_analyze_result()
    d["analisis_posible"] = False
    d["motivo_rechazo"] = "sin problemas"
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


def test_d4_analyze_result_not_possible_no_motivo():
    d = _valid_analyze_result()
    d["analisis_posible"] = False
    d["candidatos"] = []
    d["motivo_rechazo"] = None
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


def test_d5_analyze_result_bloques_incoherentes():
    d = _valid_analyze_result()
    d["bloques_procesados"] = 5
    d["bloques_totales"] = 3
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


def test_d6_analyze_result_more_than_10_candidates():
    d = _valid_analyze_result()
    d["candidatos"] = [_valid_candidate() for _ in range(11)]
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


def test_d7_analyze_result_invalid_tipo_fuente():
    d = _valid_analyze_result()
    d["tipo_fuente"] = "inventado"
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


def test_d8_analyze_result_rechazos_libres():
    d = _valid_analyze_result()
    d["rechazos"] = [{"bloque_inicio": 0, "estado": "cita_no_encontrada"}]
    m = AnalyzeResult(**d)
    assert m.rechazos[0]["estado"] == "cita_no_encontrada"


def test_d9_analyze_result_strict_source_id_as_str():
    d = _valid_analyze_result()
    d["source_id"] = "1"
    with pytest.raises(ValidationError):
        AnalyzeResult(**d)


# ===========================================================================
# GRUPO E — PersistResult (6 tests)
# ===========================================================================

def test_e1_persist_result_success():
    m = PersistResult(**_valid_persist_result())
    assert m.exito is True
    assert m.status_final == "analyzed_pending_corroboration"


def test_e2_persist_result_success_wrong_status():
    d = _valid_persist_result()
    d["status_final"] = "failed"
    with pytest.raises(ValidationError):
        PersistResult(**d)


def test_e3_persist_result_failure_no_reason():
    d = _valid_persist_result()
    d["exito"] = False
    d["status_final"] = None
    d["error_tecnico"] = None
    d["advertencias"] = []
    with pytest.raises(ValidationError):
        PersistResult(**d)


def test_e4_persist_result_failure_with_advertencias():
    d = _valid_persist_result()
    d["exito"] = False
    d["status_final"] = None
    d["error_tecnico"] = None
    d["advertencias"] = ["T3 falló"]
    m = PersistResult(**d)
    assert m.exito is False


def test_e5_persist_result_partial_reason():
    d = _valid_persist_result()
    d["partial_reason"] = "presupuesto_agotado"
    m = PersistResult(**d)
    assert m.partial_reason == "presupuesto_agotado"


def test_e6_persist_result_research_run_id_zero():
    d = _valid_persist_result()
    d["research_run_id"] = 0
    with pytest.raises(ValidationError):
        PersistResult(**d)