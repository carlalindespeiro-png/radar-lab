import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from app.skills.url_utils import normalize_url


def _check(inp, expected, label):
    out = normalize_url(inp)
    assert out == expected, (
        f"Fallo {label}:\n  in: {inp!r}\n  out: {out!r}\n  exp: {expected!r}"
    )
    print(f"  [OK] {label}: {inp!r} -> {out!r}")


def main():
    print("=== PRUEBAS DE NORMALIZACIÓN DE URLs ===\n")

    print("[Bloque 1: tracking exacto y utm_*]")
    _check("http://example.com/p?utm_id=123&id=1",
           "http://example.com/p?&id=1", "utm_id")
    _check("http://example.com/p?UTM_SOURCE_PLATFORM=x&a=2",
           "http://example.com/p?&a=2", "utm_source_platform")
    _check("http://example.com/p?fbclid=abc&gclid=def&id=3",
           "http://example.com/p?&id=3", "fbclid+gclid")
    _check("http://example.com/p?utm_source=a&utm_medium=b",
           "http://example.com/p?", "solo tracking (conserva ?)")

    print("\n[Bloque 2: codificación percentual preservada]")
    _check("http://example.com/p?q=hola%20mundo",
           "http://example.com/p?q=hola%20mundo", "%20 preservado")
    _check("http://example.com/p?q=hola+mundo",
           "http://example.com/p?q=hola+mundo", "+ preservado")
    _check("http://example.com/p?a=%2Fpath",
           "http://example.com/p?a=%2Fpath", "%2F preservado")

    print("\n[Bloque 3: parámetros sin igual, vacíos y segmentos vacíos]")
    _check("http://example.com/p?flag",
           "http://example.com/p?flag", "sin igual")
    _check("http://example.com/p?flag=",
           "http://example.com/p?flag=", "igual vacío")
    _check("http://example.com/p?a=&b=2",
           "http://example.com/p?a=&b=2", "vacío + funcional")
    _check("http://example.com/p?a=1&&b=2&",
           "http://example.com/p?a=1&&b=2&", "segmentos vacíos conservados")

    print("\n[Bloque 4: credenciales y puertos literales]")
    _check("http://User:Secret@EXAMPLE.com/p",
           "http://User:Secret@example.com/p", "userinfo intacto")
    _check("http://example.com:080/p",
           "http://example.com:080/p", "ceros iniciales")
    _check("http://example.com:abc/p",
           "http://example.com:abc/p", "puerto inválido")

    print("\n[Bloque 5: IPv6 y zone IDs]")
    _check("http://[::1]/p", "http://[::1]/p", "loopback")
    _check("http://[2001:DB8::1]:8080/p",
           "http://[2001:db8::1]:8080/p", "IPv6 minúsculas")
    _check("http://[FE80::1%25ETH0]/p",
           "http://[fe80::1%25ETH0]/p", "zone ID preservado")

    print("\n[Bloque 6: barras finales]")
    _check("http://example.com/", "http://example.com/", "raíz")
    _check("http://example.com/p/", "http://example.com/p", "una barra")
    _check("http://example.com/p//", "http://example.com/p/", "dos barras")

    print("\n[Bloque 7: query vacía y fragmentos]")
    _check("http://example.com/p?", "http://example.com/p?", "? vacío preservado")
    _check("http://example.com/p#frag", "http://example.com/p", "fragmento")
    _check("http://example.com/p?a=1#frag", "http://example.com/p?a=1", "query + fragmento")
    _check("http://example.com/p?#frag", "http://example.com/p?", "? + fragmento")

    print("\n[Bloque 8: URLs sin esquema]")
    _check("//EXAMPLE.COM/p", "//EXAMPLE.COM/p", "protocol-relative")
    _check("example.com/p", "example.com/p", "sin esquema")

    print("\n[Bloque 9: tracking codificado en el nombre]")
    _check("http://example.com/p?utm%5Fsource=x&id=1",
           "http://example.com/p?utm%5Fsource=x&id=1",
           "utm%5Fsource no reconocido")

    print("\n[Bloque 10: duplicados y orden]")
    inp = "http://example.com/p?id=1&id=2&a=3"
    out = normalize_url(inp)
    assert "id=1" in out and "id=2" in out and "a=3" in out
    assert out.index("id=1") < out.index("id=2") < out.index("a=3")
    print(f"  [OK] orden y duplicados: {out}")

    print("\n[Bloque 11: no equivalencias]")
    pairs = [
        ("http://example.com/p", "https://example.com/p", "esquema"),
        ("http://example.com/a", "http://example.com/b", "path"),
        ("http://example.com/p?id=1", "http://example.com/p?id=2", "valor"),
        ("http://example.com/p", "http://otro.com/p", "dominio"),
        ("http://example.com/p?q=a+b", "http://example.com/p?q=a%20b", "+ vs %20"),
    ]
    for u1, u2, label in pairs:
        n1, n2 = normalize_url(u1), normalize_url(u2)
        assert n1 != n2, f"Fallo NO equivalencia {label}: {n1} == {n2}"
        print(f"  [OK] {label}: {u1} != {u2}")

    print("\n[Bloque 12: segmentos vacíos alrededor de tracking]")
    _check("http://example.com/p?utm_source=x&",
           "http://example.com/p?&", "tracking + & final")
    _check("http://example.com/p?utm_source=x&&",
           "http://example.com/p?&&", "tracking + &&")
    _check("http://example.com/p?utm_source=x&&&",
           "http://example.com/p?&&&", "tracking + &&&")
    _check("http://example.com/p?utm_source=x&&id=1",
           "http://example.com/p?&&id=1", "tracking + vacío + funcional")
    _check("http://example.com/p?&id=1",
           "http://example.com/p?&id=1", "vacío inicial + funcional")
    _check("http://example.com/p?&&",
           "http://example.com/p?&&", "solo separadores")
    _check("http://example.com/p?utm_source=x&&utm_medium=y",
           "http://example.com/p?&&", "dos tracking + vacío intermedio")

    print("\n=== TODAS LAS PRUEBAS DE NORMALIZACIÓN PASARON ===")


if __name__ == "__main__":
    main()