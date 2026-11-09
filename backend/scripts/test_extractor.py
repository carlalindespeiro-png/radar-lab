import sys
import time
import random
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from app.infrastructure.extraction.content_extractor import ContentExtractor

# URLs extraídas en la Fase 4.2
URLS_FASE_4_2 = [
    "https://www.juntadeandalucia.es/organismos/avra/areas/vivienda-publica/conservacion.html",
    "https://landager.com/es/property-compliance/spain/andalusia/maintenance-obligations",
    "https://es.scribd.com/document/419786263/SAPPM201-Gestion-de-Avisos-de-Mantenimiento",
    "https://mgsolution.es/blog/automatizar-la-gestion-de-avisos-de-mantenimiento/"
]

# URLs para probar Seguridad (SSRF)
URLS_SEGURIDAD = [
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://192.168.1.1",
    "file:///C:/Windows/win.ini"
]

def main():
    extractor = ContentExtractor()

    print("=== PRUEBAS DE SEGURIDAD (SSRF) ===")
    for url in URLS_SEGURIDAD:
        res = extractor.extract(url)
        print(f"URL: {url}")
        print(f"  -> Estado: {res.status} | Motivo: {res.error_reason}\n")

    print("\n=== PRUEBAS CON URLS REALES (Fase 4.2) ===")
    exitos = 0
    total = len(URLS_FASE_4_2)

    for url in URLS_FASE_4_2:
        print(f"Analizando: {url}")
        res = extractor.extract(url)
        
        if res.status == "accessible":
            exitos += 1
            print(f"  [OK] Título: {res.title}")
            print(f"  [OK] Caracteres: {res.char_count}")
            print(f"  [OK] Fecha: {res.published_at}")
            print(f"  [OK] Inicio del texto:\n{res.text[:150]}...\n")
        else:
            print(f"  [FALLO] Estado: {res.status} | Motivo: {res.error_reason}\n")
            
        # Respetar pausas de 1.5 a 3 segundos
        time.sleep(random.uniform(1.5, 3.0))

    porcentaje = (exitos / total) * 100
    print(f"=== RESUMEN ===")
    print(f"Éxitos: {exitos}/{total} ({porcentaje:.1f}%)")
    if porcentaje >= 70.0:
        print("CRITERIO SUPERADO (>= 70%)")
    else:
        print("CRITERIO NO SUPERADO (< 70%)")

if __name__ == "__main__":
    main()