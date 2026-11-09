import urllib.request
import urllib.parse
import urllib.error
import re
from typing import List
from app.infrastructure.interfaces.search_provider import SearchProvider, SearchResult

class DuckDuckGoAdapter(SearchProvider):
    def __init__(self):
        self.base_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=data, headers=self.headers)
        
        results = []
        seen_urls = set() # Para evitar duplicados

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                # 1. Detección de bloqueo HTTP (DDG suele usar 202 para bloqueos)
                if response.status == 202:
                    print(f"   [BLOQUEO] HTTP 202 detectado para: '{query}'")
                    return []
                
                html = response.read().decode("utf-8")
                
                # 2. Detección de CAPTCHA en el HTML
                if "anomaly-modal" in html or "captcha" in html.lower():
                    print(f"   [CAPTCHA] Detectado en la respuesta para: '{query}'")
                    return []

                # 3. Extracción de resultados
                pattern = re.compile(r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>')
                matches = pattern.findall(html)

                if not matches:
                    print(f"   [SIN RESULTADOS] No se encontraron enlaces para: '{query}'")
                    return []

                for url, title in matches:
                    # Limpiar URL de redirección de DDG
                    if url.startswith("//duckduckgo.com/l/?uddg="):
                        url = urllib.parse.unquote(url.split("uddg=")[1].split("&")[0])
                    
                    # Validar que la URL sea real
                    if not url.startswith("http://") and not url.startswith("https://"):
                        continue
                        
                    # Evitar duplicados
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    results.append(SearchResult(url=url, title=title.strip(), snippet=""))
                    if len(results) >= num_results:
                        break

        except urllib.error.HTTPError as e:
            if e.code == 202:
                print(f"   [BLOQUEO] Error HTTP 202 para: '{query}'")
            else:
                print(f"   [ERROR HTTP] Código {e.code} para: '{query}'")
        except urllib.error.URLError as e:
            print(f"   [ERROR CONEXIÓN] Fallo de red: {e.reason}")
        except TimeoutError:
            print(f"   [TIMEOUT] Tiempo de espera agotado para: '{query}'")
        except Exception as e:
            print(f"   [ERROR DESCONOCIDO] {e}")
            
        return results