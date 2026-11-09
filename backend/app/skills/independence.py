from app.skills.similarity import jaccard_similarity

def classify_independence(domain_a: str, domain_b: str, text_a: str, text_b: str, url_a: str, url_b: str) -> str:
    """
    Clasifica la independencia de dos fuentes.
    Retorna: 'independencia_confirmada', 'dependencia_probable' o 'independencia_desconocida'
    """
    # Si es el mismo dominio, dependencia probable
    if domain_a == domain_b:
        return "dependencia_probable"
        
    # Si un texto cita la URL del otro, dependencia
    if url_a in text_b or url_b in text_a:
        return "dependencia_probable"
        
    # Si los textos son muy parecidos (nota de prensa replicada)
    if jaccard_similarity(text_a, text_b) > 0.90:
        return "dependencia_probable"
        
    # Si son dominios distintos, no se citan y el texto es distinto,
    # aún necesitamos confirmar si son independientes o desconocidos.
    # Aplicamos una heurística: si los textos son muy cortos, es desconocida.
    if len(text_a) < 200 or len(text_b) < 200:
        return "independencia_desconocida"
        
    # Para este MVP, si pasan todos los filtros, asumimos independencia confirmada.
    # En el futuro, aquí se podría consultar una base de datos de medios.
    return "independencia_confirmada"