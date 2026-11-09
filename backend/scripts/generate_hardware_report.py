"""
Genera un informe de hardware local sin instalar dependencias externas.
Uso: python scripts/generate_hardware_report.py
"""
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=10)
        return out.strip()
    except Exception:
        return None


def detect_cpu() -> dict:
    return {
        "processor": platform.processor() or "Desconocido",
        "architecture": platform.machine(),
        "physical_cores": os.cpu_count() or 1,
        "python_version": platform.python_version(),
    }


def detect_ram() -> dict:
    """Obtiene RAM total y disponible usando ctypes en Windows."""
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return {"total_gb": 0, "available_gb": 0, "error": "No se pudo leer la RAM"}

    return {
        "total_gb": round(stat.ullTotalPhys / (1024**3), 2),
        "available_gb": round(stat.ullAvailPhys / (1024**3), 2),
    }


def detect_gpu() -> dict:
    """Detecta GPU NVIDIA mediante nvidia-smi. Si no existe, devuelve None."""
    out = _run([
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ])
    if out is None:
        return {"available": False, "name": None, "vram_gb": 0, "cuda": False}

    parts = [p.strip() for p in out.split(",")]
    if len(parts) < 4:
        return {"available": False, "name": None, "vram_gb": 0, "cuda": False}

    name, total_mib, free_mib, driver = parts[0], float(parts[1]), float(parts[2]), parts[3]
    cuda_path = os.environ.get("CUDA_PATH")
    cuda_available = bool(cuda_path) or _run(["nvcc", "--version"]) is not None

    return {
        "available": True,
        "name": name,
        "vram_total_gb": round(total_mib / 1024, 2),
        "vram_free_gb": round(free_mib / 1024, 2),
        "driver": driver,
        "cuda": cuda_available,
    }


def detect_disk() -> dict:
    try:
        total, used, free = shutil.disk_usage("C:\\")
        return {
            "total_gb": round(total / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "used_percent": round((used / total) * 100, 1),
        }
    except Exception as exc:
        return {"error": str(exc)}


def recommend_models(hw: dict) -> list[dict]:
    """Recomienda modelos según VRAM/RAM detectadas."""
    vram = hw["gpu"].get("vram_total_gb", 0) or 0
    ram = hw["ram"].get("total_gb", 0) or 0
    models = []

    # Umbrales prácticos (Q4_K_M, contexto moderado)
    if vram >= 16:
        models.append({"model": "qwen3:14b", "params": "14B", "size_gb": 9.0, "license": "Apache 2.0", "note": "Mejor calidad en 16 GB VRAM"})
        models.append({"model": "deepseek-r1:14b", "params": "14B", "size_gb": 9.0, "license": "MIT", "note": "Razonamiento avanzado"})
    if vram >= 8 or ram >= 16:
        models.append({"model": "qwen3:8b", "params": "8B", "size_gb": 5.2, "license": "Apache 2.0", "note": "Equilibrio calidad/RAM/velocidad"})
        models.append({"model": "llama3.1:8b", "params": "8B", "size_gb": 4.9, "license": "Llama 3.1 Community", "note": "Contexto largo (128K)"})
        models.append({"model": "deepseek-r1:7b", "params": "7B", "size_gb": 4.7, "license": "MIT", "note": "Razonamiento, licencia permisiva"})
    if vram < 8 and ram < 16:
        models.append({"model": "qwen3:4b", "params": "4B", "size_gb": 2.5, "license": "Apache 2.0", "note": "Ligero para equipos modestos"})
        models.append({"model": "phi3:mini", "params": "3.8B", "size_gb": 2.3, "license": "MIT", "note": "Fallback para RAM baja"})
    return models


def build_report(hw: dict, recs: list[dict]) -> str:
    lines = [
        "# Informe de Hardware — RADAR LAB",
        f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## CPU",
        f"- Procesador: {hw['cpu']['processor']}",
        f"- Arquitectura: {hw['cpu']['architecture']}",
        f"- Núcleos lógicos: {hw['cpu']['physical_cores']}",
        "",
        "## Memoria RAM",
        f"- Total: {hw['ram']['total_gb']} GB",
        f"- Disponible: {hw['ram']['available_gb']} GB",
        "",
        "## GPU",
    ]
    gpu = hw["gpu"]
    if gpu["available"]:
        lines += [
            f"- Modelo: {gpu['name']}",
            f"- VRAM total: {gpu['vram_total_gb']} GB",
            f"- VRAM libre: {gpu['vram_free_gb']} GB",
            f"- Driver: {gpu['driver']}",
            f"- CUDA disponible: {'Sí' if gpu['cuda'] else 'No'}",
        ]
    else:
        lines.append("- No se detectó GPU NVIDIA (nvidia-smi no disponible).")
    lines += [
        "",
        "## Disco (C:)",
        f"- Total: {hw['disk'].get('total_gb', 'N/A')} GB",
        f"- Libre: {hw['disk'].get('free_gb', 'N/A')} GB",
        "",
        "## Modelos recomendados (Q4_K_M, contexto moderado)",
        "",
        "| Modelo | Params | Tamaño aprox. | Licencia | Nota |",
        "|---|---|---|---|---|",
    ]
    for m in recs:
        lines.append(f"| {m['model']} | {m['params']} | {m['size_gb']} GB | {m['license']} | {m['note']} |")
    lines.append("")
    lines.append("> **Nota:** Los tamaños son de pesos cuantizados Q4_K_M. El consumo real de RAM/VRAM es mayor por el KV cache y el runtime. Verifica con `ollama ps` tras cargar el modelo.")
    return "\n".join(lines)


def main() -> int:
    hw = {
        "cpu": detect_cpu(),
        "ram": detect_ram(),
        "gpu": detect_gpu(),
        "disk": detect_disk(),
    }
    recs = recommend_models(hw)
    report = build_report(hw, recs)

    root = Path(__file__).resolve().parent.parent.parent
    out_dir = root / "docs"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "hardware_report.md"
    if out_path.exists():
        out_path = out_dir / f"hardware_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    out_path.write_text(report, encoding="utf-8")
    print(f"Informe generado: {out_path}")
    print("\n--- RESUMEN ---")
    print(f"CPU: {hw['cpu']['processor']} ({hw['cpu']['physical_cores']} hilos)")
    print(f"RAM: {hw['ram']['total_gb']} GB total, {hw['ram']['available_gb']} GB libre")
    if hw['gpu']['available']:
        print(f"GPU: {hw['gpu']['name']} — {hw['gpu']['vram_total_gb']} GB VRAM")
    else:
        print("GPU: No detectada (sin nvidia-smi)")
    print(f"Disco libre: {hw['disk'].get('free_gb', 'N/A')} GB")
    print("\nModelos recomendados:")
    for r in recs:
        print(f"  - {r['model']} ({r['size_gb']} GB, {r['license']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())