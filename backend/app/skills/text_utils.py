import re
from typing import List, Dict, Any

def extract_entities_and_metrics(text: str) -> Dict[str, List[str]]:
    """
    Extrae fechas (años), métricas (porcentajes) y territorios básicos del texto.
    """
    # Años (ej. 2022, 2024) - Buscamos 4 dígitos que empiecen por 19 o 20
    years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
    
    # Porcentajes (ej. 20%, 15.5%) - Quitamos el \b final porque % no es carácter de palabra
    percentages = re.findall(r'(\d+(?:\.\d+)?%)', text)
    
    # Números grandes (ej. 10.000, 5000) - Evitamos capturar años que ya tenemos
    # Buscamos números con puntos de miles o de 4+ dígitos que no sean años
    numbers = re.findall(r'\b(\d{1,3}(?:\.\d{3})+|\d{4,})\b', text)
    numbers = [n for n in numbers if n not in years]
    
    # Territorios comunes (Andalucía y provincias)
    territories = []
    provincias = ["Andalucía", "Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla"]
    for prov in provincias:
        if prov.lower() in text.lower():
            territories.append(prov)
            
    return {
        "years": list(set(years)),
        "percentages": list(set(percentages)),
        "numbers": list(set(numbers)),
        "territories": list(set(territories))
    }

def normalize_text(text: str) -> str:
    """Limpia el texto para comparaciones."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text) # Quita puntuación
    return " ".join(text.split())