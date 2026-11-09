import urllib.request
import urllib.parse
import urllib.error
import socket
import ipaddress
import gzip
import zlib
import re
from html.parser import HTMLParser
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ExtractResult:
    url: str
    final_url: str
    domain: str
    title: Optional[str]
    text: str
    published_at: Optional[datetime]
    status: str  # accessible, insufficient_content, blocked, timeout, inaccessible, too_large, blocked_ssrf, unsupported_type
    error_reason: Optional[str]
    char_count: int

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validar la nueva URL antes de permitir la redirección
        if not ContentExtractor.is_safe_url(newurl):
            raise urllib.error.URLError("SSRF Blocked: Redirect to private/internal IP")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_depth = 0
        self.ignore_tags = {"script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript", "svg"}
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.ignore_tags:
            self.ignore_depth += 1
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.ignore_tags and self.ignore_depth > 0:
            self.ignore_depth -= 1
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.ignore_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

class ContentExtractor:
    def __init__(self):
        self.headers = {
            "User-Agent": "RADAR-LAB-Bot/0.1 (Research; Local)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }
        self.timeout = 10
        self.max_size = 2 * 1024 * 1024 # 2 MB

    @staticmethod
    def is_safe_url(url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            
            hostname = parsed.hostname
            if not hostname:
                return False
                
            # Resolver IP
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            
            # Bloquear IPs privadas, loopback, link-local, reservadas
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
                
            return True
        except Exception:
            return False

    def extract(self, url: str) -> ExtractResult:
        domain = urllib.parse.urlparse(url).hostname or "unknown"
        
        if not self.is_safe_url(url):
            return ExtractResult(url, url, domain, None, "", None, "blocked_ssrf", "URL no segura (SSRF)", 0)

        opener = urllib.request.build_opener(SafeRedirectHandler)
        req = urllib.request.Request(url, headers=self.headers)

        try:
            with opener.open(req, timeout=self.timeout) as response:
                # Verificar tipo de contenido
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    return ExtractResult(url, response.geturl(), domain, None, "", None, "unsupported_type", f"Tipo no soportado: {content_type}", 0)

                # Leer en streaming (máximo 2MB)
                content = b""
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    content += chunk
                    if len(content) > self.max_size:
                        return ExtractResult(url, response.geturl(), domain, None, "", None, "too_large", "Excede 2MB", 0)

                # Descomprimir si es necesario
                encoding = response.headers.get("Content-Encoding", "").lower()
                if "gzip" in encoding:
                    try:
                        content = gzip.decompress(content)
                    except Exception:
                        pass
                elif "deflate" in encoding:
                    try:
                        content = zlib.decompress(content)
                    except Exception:
                        pass

                # Detección de CAPTCHA / Bloqueo
                html_lower = content[:5000].decode("utf-8", errors="ignore").lower()
                if "captcha" in html_lower or "access denied" in html_lower or "cloudflare" in html_lower:
                    return ExtractResult(url, response.geturl(), domain, None, "", None, "blocked", "CAPTCHA/Bloqueo detectado", 0)

                # Detectar codificación
                charset = response.headers.get_content_charset()
                if not charset:
                    # Buscar en meta tags
                    meta_match = re.search(rb'<meta[^>]+charset=["\']?([a-zA-Z0-9-]+)', content[:2000], re.IGNORECASE)
                    if meta_match:
                        charset = meta_match.group(1).decode("ascii", errors="ignore")
                    else:
                        charset = "utf-8"

                try:
                    html_text = content.decode(charset, errors="replace")
                except LookupError:
                    html_text = content.decode("utf-8", errors="replace")

                # Parsear HTML
                parser = TextExtractor()
                parser.feed(html_text)
                
                final_text = "\n".join(parser.text_parts)
                final_text = re.sub(r'\n{3,}', '\n\n', final_text) # Limpiar saltos múltiples
                
                # Extraer fecha de publicación (heurística simple)
                published_at = None
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', html_text[:10000])
                if date_match:
                    try:
                        published_at = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                    except ValueError:
                        pass

                char_count = len(final_text)
                
                if char_count < 200:
                    return ExtractResult(url, response.geturl(), domain, parser.title.strip(), final_text, published_at, "insufficient_content", "Menos de 200 caracteres útiles", char_count)

                return ExtractResult(
                    url=url,
                    final_url=response.geturl(),
                    domain=domain,
                    title=parser.title.strip() or "Sin título",
                    text=final_text,
                    published_at=published_at,
                    status="accessible",
                    error_reason=None,
                    char_count=char_count
                )

        except urllib.error.HTTPError as e:
            return ExtractResult(url, url, domain, None, "", None, "inaccessible", f"HTTP {e.code}", 0)
        except urllib.error.URLError as e:
            if "SSRF Blocked" in str(e.reason):
                return ExtractResult(url, url, domain, None, "", None, "blocked_ssrf", "Redirección SSRF bloqueada", 0)
            return ExtractResult(url, url, domain, None, "", None, "connection_error", str(e.reason), 0)
        except socket.timeout:
            return ExtractResult(url, url, domain, None, "", None, "timeout", "Timeout de 10s excedido", 0)
        except Exception as e:
            return ExtractResult(url, url, domain, None, "", None, "unknown_error", str(e), 0)
            