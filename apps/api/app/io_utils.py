"""Carga, persistência e merge de payloads com input.json."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from core.config import INPUT_FILE, OUTPUT_DIR, OUTPUT_FILE

from app.schemas import CalculateRequest


def load_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail=f"JSON invalido em {path.name}: {exc}"
        ) from exc


def persist_output(result: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def merge_input(payload: CalculateRequest) -> dict:
    """Combina o input.json persistido com o payload, sem gravar em disco."""
    base = load_json(INPUT_FILE) if INPUT_FILE.exists() else {}

    if payload.origem is not None:
        base["origem"] = payload.origem
    if payload.destino is not None:
        base["destino"] = payload.destino

    if payload.modo_inicial is not None:
        base["modo_inicial"] = payload.modo_inicial
    elif payload.restricao_modal is not None:
        restr = str(payload.restricao_modal).lower()
        base["modo_inicial"] = (
            "walk" if restr in {"bus", "bus_com_acesso"} else payload.restricao_modal
        )
    else:
        base.setdefault("modo_inicial", "walk")

    if payload.algoritmo is not None:
        base["algoritmo"] = payload.algoritmo

    if payload.restricao_modal is None:
        base.pop("restricao_modal", None)
    else:
        base["restricao_modal"] = payload.restricao_modal

    return base
