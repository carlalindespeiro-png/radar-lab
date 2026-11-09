import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from app.skills.text_utils import extract_entities_and_metrics, normalize_text
from app.skills.similarity import jaccard_similarity
from app.skills.independence import classify_independence
from app.skills.contradictions import detect_contextual_contradiction
from app.skills.scoring import calculate_opportunity_score

def main():
    print("=== PRUEBAS DE SKILLS DETERMINISTAS ===\n")

    # 1. Text Utils
    texto = "En 2024, el 20% de las empresas de Andalucía perdieron 10.000 euros."
    entidades = extract_entities_and_metrics(texto)
    assert entidades["years"] == ["2024"], f"Fallo años: {entidades}"
    assert entidades["percentages"] == ["20%"], f"Fallo porcentajes: {entidades}"
    assert entidades["territories"] == ["Andalucía"], f"Fallo territorios: {entidades}"
    print("[OK] text_utils: Extracción correcta.")

    # 2. Similarity
    # Usamos frases que no compartan ninguna palabra
    assert jaccard_similarity("perro corre rápido", "gato duerme plácido") == 0.0, "Fallo: frases disjuntas deben dar 0.0"
    assert jaccard_similarity("el perro corre", "el perro corre") == 1.0, "Fallo: frases idénticas deben dar 1.0"
    print("[OK] similarity: Jaccard correcto.")

    # 3. Independence
    # Mismo dominio -> dependencia
    ind = classify_independence("foro.com", "foro.com", "texto a", "texto b", "url1", "url2")
    assert ind == "dependencia_probable", f"Fallo independencia mismo dominio: {ind}"
    # Dominios distintos pero textos cortos -> desconocida
    ind2 = classify_independence("web1.com", "web2.com", "texto corto", "otro texto corto", "url1", "url2")
    assert ind2 == "independencia_desconocida", f"Fallo independencia textos cortos: {ind2}"
    print("[OK] independence: Clasificación correcta.")

    # 4. Contradicciones
    t1 = "En 2024, el 20% de las empresas fallan."
    t2 = "En 2024, el 50% de las empresas fallan."
    assert detect_contextual_contradiction(t1, t2) == True, "Fallo: debería detectar contradicción"
    
    t3 = "En 2022, el 20% de las empresas fallan."
    t4 = "En 2024, el 50% de las empresas fallan."
    assert detect_contextual_contradiction(t3, t4) == False, "Fallo: no debería detectar contradicción (años distintos)"
    print("[OK] contradictions: Detección contextual correcta.")

    # 5. Scoring
    score = calculate_opportunity_score(
        independent_sources_count=3,
        source_types=["oficial", "foro"],
        mentions_count=4,
        severity="alta",
        software_solvable=True,
        territory_scope="comunidad",
        has_market_data=True
    )
    assert 0 <= score["score_total"] <= 100
    assert score["score_breakdown"]["quality"] > 50
    print(f"[OK] scoring: Calculado con éxito -> {score}")

    print("\n=== TODAS LAS PRUEBAS DE SKILLS PASARON ===")

if __name__ == "__main__":
    main()