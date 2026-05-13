"""FastAPI: definição do app e rotas HTTP.

O bootstrap de `sys.path` (para importar o engine) acontece em `app/__init__.py`,
que roda antes deste módulo.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.config import INPUT_FILE, OUTPUT_FILE
from core.pipeline import RouteError, run_route

from app import ENGINE_ROOT
from app.io_utils import load_json, merge_input, persist_output
from app.route_service import build_options_response
from app.schemas import CalculateRequest, OptionsRequest

app = FastAPI(title="Route API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "engine_root": str(ENGINE_ROOT),
        "has_input": INPUT_FILE.exists(),
        "has_output": OUTPUT_FILE.exists(),
    }


@app.get("/api/route")
def get_route() -> dict:
    return load_json(OUTPUT_FILE)


@app.post("/api/calculate")
def calculate(payload: CalculateRequest | None = None) -> dict:
    input_data = merge_input(payload) if payload is not None else load_json(INPUT_FILE)

    try:
        result = run_route(input_data)
    except RouteError as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)}) from exc

    persist_output(result)
    return result


@app.post("/api/options")
def calculate_options(payload: OptionsRequest | None = None) -> dict:
    base_input = load_json(INPUT_FILE)
    algorithm = payload.algoritmo if payload is not None else None
    return build_options_response(base_input, algorithm)
