from typing import Dict, Any

# Pesos iniciales configurables
WEIGHTS = {
    "quality": 0.30,
    "intensity": 0.20,
    "demand": 0.20,
    "viability": 0.15,
    "potential": 0.15
}

def calculate_opportunity_score(
    independent_sources_count: int,
    source_types: list,
    mentions_count: int,
    severity: str,
    software_solvable: bool,
    territory_scope: str,
    has_market_data: bool
) -> Dict[str, Any]:
    """
    Calcula los 5 sub-scores y el score total ponderado.
    """
    # 1. Calidad de Evidencia (0-100)
    # Basado en fuentes independientes y tipo de fuente
    quality = min(100, independent_sources_count * 30)
    if "oficial" in source_types:
        quality += 20
    quality = min(100, quality)
    
    # 2. Intensidad (0-100)
    intensity = min(100, mentions_count * 20)
    if severity == "alta":
        intensity += 30
    elif severity == "media":
        intensity += 15
    intensity = min(100, intensity)
    
    # 3. Demanda (0-100)
    # En esta fase es básico, se refinará en la Fase 5
    demand = 50 if mentions_count > 1 else 20
    if not software_solvable:
        demand = 0 # Si no se puede resolver con software, no hay demanda de software
    
    # 4. Viabilidad (0-100)
    viability = 100 if software_solvable else 10
    
    # 5. Potencial Económico (0-100)
    potential = 30
    if territory_scope == "comunidad":
        potential += 20
    elif territory_scope == "provincia":
        potential += 10
    if has_market_data:
        potential += 30
    potential = min(100, potential)
    
    # Cálculo ponderado
    total = int(
        (quality * WEIGHTS["quality"]) +
        (intensity * WEIGHTS["intensity"]) +
        (demand * WEIGHTS["demand"]) +
        (viability * WEIGHTS["viability"]) +
        (potential * WEIGHTS["potential"])
    )
    
    return {
        "score_total": total,
        "score_breakdown": {
            "quality": quality,
            "intensity": intensity,
            "demand": demand,
            "viability": viability,
            "potential": potential
        }
    }