import urllib.parse

_TRACKING_EXACT = {"fbclid", "gclid"}


def _is_tracking_name(name: str) -> bool:
    name_lower = name.lower()
    if name_lower in _TRACKING_EXACT:
        return True
    if name_lower.startswith("utm_"):
        return True
    return False


def _split_netloc(netloc: str):
    userinfo = ""
    rest = netloc
    if "@" in rest:
        idx = rest.rfind("@")
        userinfo = rest[: idx + 1]
        rest = rest[idx + 1 :]

    if rest.startswith("["):
        end = rest.find("]")
        if end == -1:
            return userinfo, rest, ""
        return userinfo, rest[: end + 1], rest[end + 1 :]

    if ":" in rest:
        idx = rest.rfind(":")
        return userinfo, rest[:idx], rest[idx:]

    return userinfo, rest, ""


def _normalize_host(host: str) -> str:
    if host.startswith("[") and host.endswith("]"):
        inner = host[1:-1]
        if "%" in inner:
            ip, zone = inner.split("%", 1)
            return f"[{ip.lower()}%{zone}]"
        return f"[{inner.lower()}]"
    return host.lower()


def _build_netloc(netloc: str) -> str:
    userinfo, host, port = _split_netloc(netloc)
    return f"{userinfo}{_normalize_host(host)}{port}"


def _filter_query(query: str) -> str:
    if not query:
        return ""
    segments = query.split("&")
    n = len(segments)
    survives = [not _is_tracking_name(seg.split("=", 1)[0]) for seg in segments]

    result = ""
    for i, seg in enumerate(segments):
        if survives[i]:
            result += seg
        if i < n - 1 and (survives[i] or survives[i + 1]):
            result += "&"
    return result


def _normalize_path(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        return path[:-1]
    return path


def _has_question_mark(url: str) -> bool:
    url_no_fragment = url.split("#", 1)[0]
    return "?" in url_no_fragment


def normalize_url(url) -> str:
    if not isinstance(url, str):
        return "" if url is None else str(url).strip()

    url = url.strip()
    if not url:
        return ""

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return url

    if not parsed.scheme or not parsed.netloc:
        return url

    try:
        scheme = parsed.scheme.lower()
        netloc = _build_netloc(parsed.netloc)
        path = _normalize_path(parsed.path)
        params = parsed.params
        new_query = _filter_query(parsed.query)

        result = urllib.parse.urlunparse(
            (scheme, netloc, path, params, new_query, "")
        )

        if not new_query and _has_question_mark(url):
            result += "?"

        return result
    except Exception:
        return url