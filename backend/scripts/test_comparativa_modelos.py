import json
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

TEXTOS = [
    "Texto original: 'Los administradores de fincas de Andalucía se quejan de que la coordinación de reparaciones es un caos, ya que cada técnico les envía presupuestos en formatos distintos y no tienen una trazabilidad clara de las incidencias.'",
    "Texto original: 'Según el INE, en 2023 había 12.450 empresas de mantenimiento y reparación de inmuebles en Andalucía, un 3,2% más que el año anterior.'",
    "Texto original: 'Los técnicos autónomos de reparaciones se quejan de que pierden mucho tiempo haciendo presupuestos manuales en Word y luego los clientes no les contestan o les regatean el precio.'"
]

SYSTEM_PROMPT = (
    "Eres un analista de RADAR LAB. Extrae información del texto y clasifica la "
    "afirmación principal como 'hecho' (dato verificable con fuente), 'estimacion' "
    "(cálculo o aproximación) o 'hipotesis' (queja, opinión o problema no verificado). "
    "Responde ÚNICAMENTE con un objeto JSON válido."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "problema_principal": {"type": "string"},
        "sector": {"type": "string"},
        "tipo_afirmacion": {"type": "string", "enum": ["hecho", "estimacion", "hipotesis"]},
    },
    "required": ["problema_principal", "sector", "tipo_afirmacion"],
}

def ejecutar(modelo: str, texto: str) -> dict:
    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": texto},
        ],
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0.0},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})

    inicio = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        resultado = json.loads(resp.read().decode("utf-8"))
    duracion = time.time() - inicio

    contenido = json.loads(resultado["message"]["content"])
    contenido["_tiempo_segundos"] = round(duracion, 2)
    return contenido

def main():
    for modelo in ["qwen2.5:1.5b", "qwen2.5:3b"]:
        print(f"\n=== MODELO: {modelo} ===")
        for i, texto in enumerate(TEXTOS, 1):
            try:
                r = ejecutar(modelo, texto)
                print(f"\n  Prueba {i}:")
                print(f"    Problema: {r.get('problema_principal')}")
                print(f"    Sector:   {r.get('sector')}")
                print(f"    Tipo:     {r.get('tipo_afirmacion')}")
                print(f"    Tiempo:   {r.get('_tiempo_segundos')} s")
            except Exception as exc:
                print(f"\n  Prueba {i}: ERROR — {exc}")

if __name__ == "__main__":
    main()