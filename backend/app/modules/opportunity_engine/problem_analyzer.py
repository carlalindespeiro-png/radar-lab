import json
import urllib.request
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.opportunity_engine.prompts import PROBLEM_ANALYZER_SYSTEM_PROMPT

# ---------- CONFIGURACIÓN (CON FALLBACK DEFENSIVO) ----------
try:
    from app.core.config import settings as _settings
    _DEFAULT_URL = getattr(_settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    _DEFAULT_MODEL = getattr(_settings, "PROBLEM_ANALYZER_MODEL", "qwen2.5:1.5b")
except Exception:
    _DEFAULT_URL = "http://127.0.0.1:11434"
    _DEFAULT_MODEL = "qwen2.5:1.5b"


# ---------- MODELOS PYDANTIC ----------
class LLMCandidateModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    evidencia_cita: str = Field(..., min_length=1, max_length=1000)
    clasificacion_evidencia: str = Field(
        ..., pattern="^(afirmacion_explicita|dato_presentado_como_hecho|estimacion)$"
    )
    interpretacion_problema: str = Field(..., min_length=1, max_length=500)
    nivel_inferencia: str = Field(
        ..., pattern="^(literal|inferencia_directa|hipotesis_analista)$"
    )
    limitaciones_evidencia: str = Field(..., max_length=300)
    solucion_existente_mencionada: str = Field(..., max_length=300)
    es_empresa_competidora: bool
    necesidad_software_inferida: bool


class LLMResponseModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    analisis_posible: bool
    motivo_rechazo: Optional[str] = Field(..., max_length=300)
    tipo_fuente: str = Field(
        ..., pattern="^(manual|institucional|comercial|foro|noticia|desconocido)$"
    )
    candidatos: List[Any] = Field(..., max_length=10)


# ---------- ESQUEMA OLLAMA ----------
OLLAMA_FORMAT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "analisis_posible": {"type": "boolean"},
        "motivo_rechazo": {"type": ["string", "null"], "maxLength": 300},
        "tipo_fuente": {
            "type": "string",
            "enum": ["manual", "institucional", "comercial", "foro", "noticia", "desconocido"],
        },
        "candidatos": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "evidencia_cita": {"type": "string", "maxLength": 1000},
                    "clasificacion_evidencia": {
                        "type": "string",
                        "enum": ["afirmacion_explicita", "dato_presentado_como_hecho", "estimacion"],
                    },
                    "interpretacion_problema": {"type": "string", "maxLength": 500},
                    "nivel_inferencia": {
                        "type": "string",
                        "enum": ["literal", "inferencia_directa", "hipotesis_analista"],
                    },
                    "limitaciones_evidencia": {"type": "string", "maxLength": 300},
                    "solucion_existente_mencionada": {"type": "string", "maxLength": 300},
                    "es_empresa_competidora": {"type": "boolean"},
                    "necesidad_software_inferida": {"type": "boolean"},
                },
                "required": [
                    "evidencia_cita", "clasificacion_evidencia", "interpretacion_problema",
                    "nivel_inferencia", "limitaciones_evidencia", "solucion_existente_mencionada",
                    "es_empresa_competidora", "necesidad_software_inferida",
                ],
            },
        },
    },
    "required": ["analisis_posible", "motivo_rechazo", "tipo_fuente", "candidatos"],
}


class ProblemAnalyzer:
    def __init__(
        self,
        llm_callable: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.ollama_url = ollama_url or _DEFAULT_URL
        self.model = model or _DEFAULT_MODEL
        self.max_chars_per_block = 6000
        self.overlap_chars = 500
        self.llm_callable = llm_callable or self._call_ollama

    def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        url = f"{self.ollama_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": PROBLEM_ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": OLLAMA_FORMAT_SCHEMA,
            "options": {"temperature": 0.0},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return json.loads(result["message"]["content"])
        except Exception:
            return None

    def _split_into_blocks(self, text: str) -> List[tuple]:
        n = len(text)
        if n <= self.max_chars_per_block:
            return [(text, 0, n)]
        step = self.max_chars_per_block - self.overlap_chars
        blocks = []
        start = 0
        while start < n:
            end = min(start + self.max_chars_per_block, n)
            blocks.append((text[start:end], start, end))
            if end == n:
                break
            start += step
        return blocks

    def _find_all_appearances(
        self, full_text: str, citation: str, block_start: int, block_end: int
    ) -> List[tuple]:
        appearances = []
        idx = block_start
        while True:
            idx = full_text.find(citation, idx, block_end)
            if idx == -1:
                break
            end = idx + len(citation)
            if end > block_end:
                break
            if full_text[idx:end] == citation:
                appearances.append((idx, end))
            idx = end
        return appearances

    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        merged = []
        for cand in candidates:
            found = False
            for m in merged:
                same_interp = cand["interpretacion_problema"] == m["interpretacion_problema"]
                same_cita = cand["evidencias"][0]["cita_literal"] == m["evidencias"][0]["cita_literal"]
                if same_interp and same_cita:
                    for new_ev in cand["evidencias"]:
                        is_dup = any(
                            e["posicion_inicio"] == new_ev["posicion_inicio"]
                            and e["posicion_fin"] == new_ev["posicion_fin"]
                            for e in m["evidencias"]
                        )
                        if not is_dup:
                            m["evidencias"].append(new_ev)
                    found = True
                    break
            if not found:
                merged.append(cand)
        return merged

    def analyze(self, text: str, source_id: int, url: str, titulo: str) -> Dict[str, Any]:
        blocks = self._split_into_blocks(text)
        all_candidates: List[Dict] = []
        all_rechazos: List[Dict] = []
        tipo_fuente_votos: List[str] = []
        motivos_rechazo: List[str] = []

        for block_text, block_start, block_end in blocks:
            prompt = json.dumps({"texto_fuente": block_text}, ensure_ascii=False)

            try:
                response = self.llm_callable(prompt)
            except Exception as e:
                all_rechazos.append({
                    "bloque_inicio": block_start,
                    "estado": "error_llm",
                    "error": str(e),
                })
                continue

            if response is None:
                all_rechazos.append({
                    "bloque_inicio": block_start,
                    "estado": "error_llm",
                    "error": "Sin respuesta del LLM",
                })
                continue

            if not isinstance(response, dict):
                all_rechazos.append({
                    "bloque_inicio": block_start,
                    "estado": "error_estructura_llm",
                    "error": "La respuesta del LLM no es un diccionario",
                })
                continue

            try:
                validated = LLMResponseModel(**response)
            except ValidationError as e:
                all_rechazos.append({
                    "bloque_inicio": block_start,
                    "estado": "error_estructura_llm",
                    "error": str(e.errors()),
                })
                continue

            tipo_fuente_votos.append(validated.tipo_fuente)

            if validated.analisis_posible and len(validated.candidatos) == 0:
                all_rechazos.append({
                    "bloque_inicio": block_start,
                    "estado": "error_coherencia",
                    "error": "analisis_posible=True sin candidatos",
                })
                continue
            if not validated.analisis_posible and len(validated.candidatos) > 0:
                all_rechazos.append({
                    "bloque_inicio": block_start,
                    "estado": "error_coherencia",
                    "error": "analisis_posible=False con candidatos",
                })
                continue

            if not validated.analisis_posible:
                if validated.motivo_rechazo:
                    motivos_rechazo.append(validated.motivo_rechazo)
                continue

            used_offsets = set()
            for idx_c, cand_dict in enumerate(validated.candidatos):
                if not isinstance(cand_dict, dict):
                    all_rechazos.append({
                        "bloque_inicio": block_start,
                        "indice_candidato": idx_c,
                        "estado": "error_validacion_candidato",
                        "error": "El candidato no es un diccionario",
                    })
                    continue

                try:
                    cand = LLMCandidateModel(**cand_dict)
                except ValidationError as e:
                    all_rechazos.append({
                        "bloque_inicio": block_start,
                        "indice_candidato": idx_c,
                        "estado": "error_validacion_candidato",
                        "error": str(e.errors()),
                    })
                    continue

                appearances = self._find_all_appearances(
                    text, cand.evidencia_cita, block_start, block_end
                )
                available = [(s, e) for (s, e) in appearances if (s, e) not in used_offsets]

                if not available:
                    all_rechazos.append({
                        "bloque_inicio": block_start,
                        "indice_candidato": idx_c,
                        "evidencia_cita": cand.evidencia_cita,
                        "estado": "rechazado_cita_no_encontrada",
                    })
                    continue

                start, end = available[0]
                used_offsets.add((start, end))

                all_candidates.append({
                    "interpretacion_problema": cand.interpretacion_problema,
                    "nivel_inferencia": cand.nivel_inferencia,
                    "necesidad_software_inferida": cand.necesidad_software_inferida,
                    "es_empresa_competidora": cand.es_empresa_competidora,
                    "solucion_existente_mencionada": cand.solucion_existente_mencionada,
                    "evidencias": [{
                        "cita_literal": cand.evidencia_cita,
                        "clasificacion_evidencia": cand.clasificacion_evidencia,
                        "posicion_inicio": start,
                        "posicion_fin": end,
                        "limitaciones_evidencia": cand.limitaciones_evidencia,
                    }],
                })

        dedup = self._deduplicate_candidates(all_candidates)

        tipo_fuente_final = "desconocido"
        if tipo_fuente_votos:
            tipo_fuente_final = Counter(tipo_fuente_votos).most_common(1)[0][0]

        analisis_posible_final = len(dedup) > 0
        motivo_rechazo_final = None
        if not analisis_posible_final:
            motivos_unicos = list(dict.fromkeys(motivos_rechazo))
            motivo_rechazo_final = (
                " | ".join(motivos_unicos) if motivos_unicos
                else "No se encontraron problemas válidos"
            )

        return {
            "source_id": source_id,
            "url": url,
            "titulo": titulo,
            "analisis_posible": analisis_posible_final,
            "tipo_fuente": tipo_fuente_final,
            "motivo_rechazo": motivo_rechazo_final,
            "candidatos": dedup,
            "rechazos": all_rechazos,
        }