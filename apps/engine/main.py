#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI: lê input.json, executa o pipeline e grava output/output.json."""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from core.config import INPUT_FILE, OUTPUT_DIR, OUTPUT_FILE
from core.pipeline import run_route, RouteError


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("route")

    if not INPUT_FILE.exists():
        log.error("input.json não encontrado")
        return 1

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        input_data = json.load(f)

    log.info("Origem: %s", input_data.get("origem"))
    log.info("Destino: %s", input_data.get("destino"))
    log.info("Modal inicial: %s", input_data.get("modo_inicial"))

    try:
        result = run_route(input_data)
    except RouteError as e:
        log.error("Erro: %s", e)
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    resumo = result["resumo"]
    print("\n" + "=" * 60)
    print("RESUMO DA ROTA")
    print("=" * 60)
    print(f"Tempo total:      {resumo['tempo_total']} horas")
    print(f"Custo total:      R$ {resumo['custo_total']:.2f}")
    print(f"Distância:        {resumo['distancia_total']:.2f} km")
    print(f"Risco médio:      {resumo['risco_medio']:.3f}")
    print(f"Velocidade média: {resumo['velocidade_media_total']:.2f} km/h")
    print(f"Segmentos:        {len(result['segments'])}")
    print(f"Arestas:          {len(result['edges'])}")
    print("=" * 60)
    print(f"Saída: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
