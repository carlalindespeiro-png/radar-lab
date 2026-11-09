import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
from app.infrastructure.interfaces.llm_provider import LLMProvider

class OllamaAdapter(LLMProvider):
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:1.5b"):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        
        system_prompt = (
            "Eres un analista de RADAR LAB. Tu única tarea es extraer información del texto. "
            "Debes clasificar la afirmación como 'hecho' (solo si hay datos verificables) "
            "o 'hipotesis' (si es una queja u opinión). "
            "Responde ÚNICAMENTE con un objeto JSON válido."
        )
        
        ollama_format = {
            "type": "object",
            "properties": {
                "problema_principal": {"type": "string"},
                "sector": {"type": "string"},
                "tipo_afirmacion": {"type": "string", "enum": ["hecho", "hipotesis"]}
            },
            "required": ["problema_principal", "sector", "tipo_afirmacion"]
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": ollama_format,
            "options": {"temperature": 0.0}
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result["message"]["content"]
                return json.loads(content)
        except urllib.error.URLError as e:
            raise Exception(f"Error conectando con Ollama: {e.reason}. ¿Está Ollama ejecutándose?")
        except Exception as e:
            raise Exception(f"Error procesando la respuesta de la IA: {str(e)}")