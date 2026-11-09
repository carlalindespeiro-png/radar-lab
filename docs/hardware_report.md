# Informe de Hardware — RADAR LAB
**Fecha:** 2026-11-04 16:43:21

## CPU
- Procesador: Intel64 Family 6 Model 158 Stepping 13, GenuineIntel
- Arquitectura: AMD64
- Núcleos lógicos: 8

## Memoria RAM
- Total: 15.88 GB
- Disponible: 2.6 GB

## GPU
- No se detectó GPU NVIDIA (nvidia-smi no disponible).

## Disco (C:)
- Total: 930.87 GB
- Libre: 373.01 GB

## Modelos recomendados (Q4_K_M, contexto moderado)

| Modelo | Params | Tamaño aprox. | Licencia | Nota |
|---|---|---|---|---|
| qwen3:4b | 4B | 2.5 GB | Apache 2.0 | Ligero para equipos modestos |
| phi3:mini | 3.8B | 2.3 GB | MIT | Fallback para RAM baja |

> **Nota:** Los tamaños son de pesos cuantizados Q4_K_M. El consumo real de RAM/VRAM es mayor por el KV cache y el runtime. Verifica con `ollama ps` tras cargar el modelo.