import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from app.modules.opportunity_engine.query_builder import QueryBuilder
from app.infrastructure.search.ddg_adapter import DuckDuckGoAdapter

def main():
    print("=== 1. Generando consultas operativas (versión final) ===")
    qb = QueryBuilder()
    queries = qb.build_queries("Mantenimiento y reparacion de inmuebles", "Andalucia")
    for q in queries:
        print(f"   -> {q}")

    print("\n=== 2. Probando Buscador (DuckDuckGo) ===")
    search = DuckDuckGoAdapter()
    
    # Probamos la primera consulta (gestión de avisos en foros)
    for test_query in queries[:2]:
        print(f"\n--- Buscando: '{test_query}' ---")
        results = search.search(test_query, num_results=3)
        
        if results:
            print(f"   Se han encontrado {len(results)} resultados únicos:")
            for i, r in enumerate(results, 1):
                print(f"   [{i}] {r.title}")
                print(f"       {r.url}")
        else:
            print("   No se devolvieron resultados o hubo un error controlado.")

if __name__ == "__main__":
    main()