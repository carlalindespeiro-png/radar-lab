from app.skills.text_utils import extract_entities_and_metrics

def detect_contextual_contradiction(text_a: str, text_b: str) -> bool:
    """
    Compara dos textos. Devuelve True si hay una contradicción métrica
    en el mismo contexto (misma fecha/territorio).
    """
    ent_a = extract_entities_and_metrics(text_a)
    ent_b = extract_entities_and_metrics(text_b)
    
    # Si no hay métricas en alguno, no podemos detectar contradicción numérica
    if not ent_a["percentages"] and not ent_a["numbers"]:
        return False
    if not ent_b["percentages"] and not ent_b["numbers"]:
        return False
        
    # Verificar si comparten contexto (ej. mismo año o mismo territorio)
    mismo_contexto = False
    if ent_a["years"] and ent_b["years"]:
        if set(ent_a["years"]).intersection(set(ent_b["years"])):
            mismo_contexto = True
    if ent_a["territories"] and ent_b["territories"]:
        if set(ent_a["territories"]).intersection(set(ent_b["territories"])):
            mismo_contexto = True
            
    # Si no comparten contexto, no es una contradicción directa
    if not mismo_contexto:
        return False
        
    # Si comparten contexto pero las métricas son diferentes, es un conflicto
    # (Esto es simplificado, en producción requeriría análisis semántico)
    if set(ent_a["percentages"]) != set(ent_b["percentages"]):
        return True
        
    return False