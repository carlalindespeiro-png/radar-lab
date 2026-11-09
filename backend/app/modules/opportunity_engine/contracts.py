"""Contratos Pydantic para el pipeline de RADAR LAB.

Contratos:
  - AnalyzeInput
  - AnalyzeResult
  - Candidate
  - EvidenceContract
  - PersistResult

Decisiones aplicadas (D-1 a D-8):
  - D-1: sin analyzer_version.
  - D-2: validador de coherencia de bloques.
  - D-3: solucion_existente_mencionada str|None.
  - D-4: validador de posiciones.
  - D-5: validador de coherencia en PersistResult.
  - D-6: strict solo en AnalyzeResult y Candidate.
  - D-7: rechazos libres.
  - D-8: nombre EvidenceContract.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHA256_HEX_PATTERN = r"^[0-9a-f]{64}$"

TipoFuente = Literal[
    "manual", "institucional", "comercial", "foro", "noticia", "desconocido"
]
NivelInferencia = Literal["literal", "inferencia_directa", "hipotesis_analista"]
ClasificacionEvidencia = Literal[
    "afirmacion_explicita", "dato_presentado_como_hecho", "estimacion"
]
StatusFinal = Literal[
    "analyzed_pending_corroboration", "partial_failure", "failed"
]
PartialReason = Literal["presupuesto_agotado"]


class AnalyzeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)
    source_id: int = Field(..., ge=1)
    extract_id: int = Field(..., ge=1)
    research_run_id: int = Field(..., ge=1)
    url: str = Field(..., min_length=1)
    titulo: str = Field(default="", max_length=500)
    tipo_fuente_previo: TipoFuente | None = None


class EvidenceContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cita_literal: str = Field(..., min_length=1, max_length=1000)
    clasificacion_evidencia: ClasificacionEvidencia
    posicion_inicio: int | None = Field(default=None, ge=0)
    posicion_fin: int | None = Field(default=None, ge=0)
    limitaciones_evidencia: str = Field(default="", max_length=300)
    cita_hash: str = Field(..., pattern=SHA256_HEX_PATTERN)

    @model_validator(mode="after")
    def _check_positions(self):
        if self.posicion_inicio is not None and self.posicion_fin is not None:
            if self.posicion_fin < self.posicion_inicio:
                raise ValueError("posicion_fin must be >= posicion_inicio")
        return self


class Candidate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    interpretacion_problema: str = Field(..., min_length=1, max_length=500)
    normalized_text: str = Field(..., min_length=1)
    normalized_hash: str = Field(..., pattern=SHA256_HEX_PATTERN)
    nivel_inferencia: NivelInferencia
    necesidad_software_inferida: bool
    es_empresa_competidora: bool
    solucion_existente_mencionada: str | None = Field(default=None, max_length=300)
    confidence_inicial: int = Field(..., ge=0, le=100)
    assertion_hash: str = Field(..., pattern=SHA256_HEX_PATTERN)
    evidencias: list[EvidenceContract] = Field(..., min_length=1)


class AnalyzeResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source_id: int = Field(..., ge=1)
    extract_id: int = Field(..., ge=1)
    research_run_id: int = Field(..., ge=1)
    url: str
    titulo: str = Field(default="", max_length=500)
    analisis_posible: bool
    tipo_fuente: TipoFuente
    motivo_rechazo: str | None = Field(default=None, max_length=300)
    candidatos: list[Candidate] = Field(..., max_length=10)
    rechazos: list[dict] = Field(default_factory=list)
    presupuesto_agotado: bool
    bloques_procesados: int = Field(..., ge=0)
    bloques_totales: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _check_coherence(self):
        if self.bloques_procesados > self.bloques_totales:
            raise ValueError("bloques_procesados must be <= bloques_totales")
        if self.analisis_posible and not self.candidatos:
            raise ValueError("analisis_posible=True requires at least 1 candidate")
        if not self.analisis_posible and self.candidatos:
            raise ValueError("analisis_posible=False cannot have candidates")
        if not self.analisis_posible and not self.motivo_rechazo:
            raise ValueError("analisis_posible=False requires motivo_rechazo")
        return self


class PersistResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_run_id: int = Field(..., ge=1)
    extract_id: int = Field(..., ge=1)
    exito: bool
    problems_creados: int = Field(default=0, ge=0)
    problems_reutilizados: int = Field(default=0, ge=0)
    assertions_creadas: int = Field(default=0, ge=0)
    assertions_reutilizadas: int = Field(default=0, ge=0)
    evidence_creadas: int = Field(default=0, ge=0)
    evidence_omitidas: int = Field(default=0, ge=0)
    source_type_actualizado: bool = False
    status_final: StatusFinal | None = None
    partial_reason: PartialReason | None = None
    error_tecnico: str | None = None
    advertencias: list[str] = Field(default_factory=list)
    bloques_procesados: int = Field(default=0, ge=0)
    bloques_totales: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check_status_coherence(self):
        if self.exito and self.status_final != "analyzed_pending_corroboration":
            raise ValueError(
                "exito=True requires status_final='analyzed_pending_corroboration'"
            )
        if not self.exito and self.status_final == "analyzed_pending_corroboration":
            raise ValueError(
                "exito=False cannot have status_final='analyzed_pending_corroboration'"
            )
        if not self.exito and not (
            self.error_tecnico or self.status_final or self.advertencias
        ):
            raise ValueError(
                "exito=False requires error_tecnico, status_final or advertencias"
            )
        return self