from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "input.json"
OUTPUT_FILE = PROJECT_ROOT / "output.json"
WEIGHTS = {"time": 0.5, "cost": 0.3, "risk": 0.2}

OPTION_SCENARIOS = [
    {
        "id": "multimodal_walk",
        "label": "Multimodal (a pe + trocas)",
        "modo_inicial": "walk",
        "restricao_modal": None,
    },
    {
        "id": "walk_only",
        "label": "Todo a pe",
        "modo_inicial": "walk",
        "restricao_modal": "walk",
    },
    {
        "id": "bike_only",
        "label": "Somente bike",
        "modo_inicial": "bike",
        "restricao_modal": "bike",
    },
    {
        "id": "car_only",
        "label": "Somente carro",
        "modo_inicial": "car",
        "restricao_modal": "car",
    },
    {
        "id": "moto_only",
        "label": "Somente moto",
        "modo_inicial": "moto",
        "restricao_modal": "moto",
    },
    {
        "id": "bus_only",
        "label": "Somente onibus",
        "modo_inicial": "bus",
        "restricao_modal": "bus",
    },
    {
        "id": "bus_with_access",
        "label": "Onibus com acesso a pe",
        "modo_inicial": "walk",
        "restricao_modal": "bus_com_acesso",
    },
    {
        "id": "uber_car_only",
        "label": "Somente uber carro",
        "modo_inicial": "uber_car",
        "restricao_modal": "uber_car",
    },
    {
        "id": "uber_moto_only",
        "label": "Somente uber moto",
        "modo_inicial": "uber_moto",
        "restricao_modal": "uber_moto",
    },
]


class CalculateRequest(BaseModel):
    origem: list[float] | None = Field(default=None, description="[lat, lon]")
    destino: list[float] | None = Field(default=None, description="[lat, lon]")
    modo_inicial: str | None = Field(
        default=None,
        description="walk|bike|car|moto|bus|uber_car|uber_moto",
    )
    algoritmo: str | None = Field(default=None, description="dijkstra|astar")
    restricao_modal: str | None = Field(
        default=None,
        description="forca modal unico ou modo especial bus_com_acesso",
    )

    @model_validator(mode="after")
    def validate_coordinates(self) -> "CalculateRequest":
        for field_name in ("origem", "destino"):
            coords = getattr(self, field_name)
            if coords is None:
                continue
            if len(coords) != 2:
                raise ValueError(f"{field_name} precisa ter 2 valores: [lat, lon]")
        if self.algoritmo is not None and self.algoritmo not in {"dijkstra", "astar"}:
            raise ValueError("algoritmo deve ser dijkstra ou astar")
        return self


class OptionsRequest(BaseModel):
    algoritmo: str | None = Field(default=None, description="dijkstra|astar")

    @model_validator(mode="after")
    def validate_algorithm(self) -> "OptionsRequest":
        if self.algoritmo is not None and self.algoritmo not in {"dijkstra", "astar"}:
            raise ValueError("algoritmo deve ser dijkstra ou astar")
        return self


app = FastAPI(title="Route API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo nao encontrado: {path.name}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail=f"JSON invalido em {path.name}: {exc}"
        ) from exc


def _write_input(payload: CalculateRequest) -> None:
    existing = _load_json(INPUT_FILE)

    if payload.origem is not None:
        existing["origem"] = payload.origem
    if payload.destino is not None:
        existing["destino"] = payload.destino
    # Em recálculos sem modo explícito:
    # - se houver restrição de modal, inicia naquele modal (ex.: bus-only)
    # - senão, volta ao padrão multimodal iniciando a pé.
    if payload.modo_inicial is not None:
        existing["modo_inicial"] = payload.modo_inicial
    elif payload.restricao_modal is not None:
        if str(payload.restricao_modal).lower() in {"bus", "bus_com_acesso"}:
            existing["modo_inicial"] = "walk"
        else:
            existing["modo_inicial"] = payload.restricao_modal
    else:
        existing["modo_inicial"] = "walk"
    if payload.algoritmo is not None:
        existing["algoritmo"] = payload.algoritmo
    # Se nao vier restricao no payload, remove qualquer restricao antiga persistida.
    if payload.restricao_modal is None:
        existing.pop("restricao_modal", None)
    else:
        existing["restricao_modal"] = payload.restricao_modal

    INPUT_FILE.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_input_dict(payload: dict) -> None:
    INPUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _run_calculation() -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "main.py"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=1200,
    )

    return completed


def _normalize(value: float, min_val: float, max_val: float) -> float:
    range_val = max_val - min_val
    if range_val == 0:
        return 0.5
    result = (value - min_val) / range_val
    return max(0.0, min(1.0, result))


def _compute_ranking(options: list[dict]) -> list[dict]:
    valid = [opt for opt in options if opt.get("status") == "ok"]
    if not valid:
        return options

    times = [float(opt["resumo"].get("tempo_total", 0.0)) for opt in valid]
    costs = [float(opt["resumo"].get("custo_total", 0.0)) for opt in valid]
    risks = [float(opt["resumo"].get("risco_medio", 0.0)) for opt in valid]

    min_time, max_time = min(times), max(times)
    min_cost, max_cost = min(costs), max(costs)
    min_risk, max_risk = min(risks), max(risks)

    for opt in valid:
        resumo = opt["resumo"]
        tempo_norm = _normalize(float(resumo.get("tempo_total", 0.0)), min_time, max_time)
        custo_norm = _normalize(float(resumo.get("custo_total", 0.0)), min_cost, max_cost)
        risco_norm = _normalize(float(resumo.get("risco_medio", 0.0)), min_risk, max_risk)

        score = (
            WEIGHTS["time"] * tempo_norm
            + WEIGHTS["cost"] * custo_norm
            + WEIGHTS["risk"] * risco_norm
        )

        opt["score"] = round(score, 6)

    sorted_valid = sorted(valid, key=lambda item: item["score"])
    rank_map = {item["id"]: idx + 1 for idx, item in enumerate(sorted_valid)}

    for opt in options:
        if opt.get("status") == "ok":
            opt["rank"] = rank_map.get(opt["id"])
        else:
            opt["rank"] = None
            opt["score"] = None

    return options


def _run_scenario(base_input: dict, scenario: dict, algorithm: str | None) -> dict:
    scenario_input = dict(base_input)
    scenario_input["modo_inicial"] = scenario["modo_inicial"]
    if algorithm:
        scenario_input["algoritmo"] = algorithm

    restricao_modal = scenario.get("restricao_modal")
    if restricao_modal:
        scenario_input["restricao_modal"] = restricao_modal
    else:
        scenario_input.pop("restricao_modal", None)

    _write_input_dict(scenario_input)
    completed = _run_calculation()

    if completed.returncode != 0 or not OUTPUT_FILE.exists():
        return {
            "id": scenario["id"],
            "label": scenario["label"],
            "modo_inicial": scenario["modo_inicial"],
            "restricao_modal": restricao_modal,
            "status": "error",
            "error": {
                "message": "Falha ao calcular este cenario",
                "returncode": completed.returncode,
                "stderr": completed.stderr[-3000:],
                "stdout": completed.stdout[-3000:],
            },
        }

    route_data = _load_json(OUTPUT_FILE)

    return {
        "id": scenario["id"],
        "label": scenario["label"],
        "modo_inicial": scenario["modo_inicial"],
        "restricao_modal": restricao_modal,
        "status": "ok",
        "resumo": route_data.get("resumo", {}),
        "segments_count": len(route_data.get("segments", [])),
        "edges_count": len(route_data.get("edges", [])),
        "route": route_data,
    }


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "project_root": str(PROJECT_ROOT),
        "has_input": INPUT_FILE.exists(),
        "has_output": OUTPUT_FILE.exists(),
    }


@app.get("/api/route")
def get_route() -> dict:
    return _load_json(OUTPUT_FILE)


@app.post("/api/calculate")
def calculate(payload: CalculateRequest | None = None) -> dict:
    if payload is not None:
        _write_input(payload)

    completed = _run_calculation()
    stdout = completed.stdout
    stderr = completed.stderr

    if completed.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Falha ao executar calculo do backend Python",
                "returncode": completed.returncode,
                "stderr": stderr[-3000:],
                "stdout": stdout[-3000:],
            },
        )

    if not OUTPUT_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Calculo executado sem gerar output.json",
                "stderr": stderr[-3000:],
                "stdout": stdout[-3000:],
            },
        )

    if stderr.strip():
        # Mantem retorno de sucesso com aviso quando o script escreveu em stderr.
        route_data = _load_json(OUTPUT_FILE)
        route_data["warning"] = stderr[-1200:]
        return route_data

    return _load_json(OUTPUT_FILE)


@app.post("/api/options")
def calculate_options(payload: OptionsRequest | None = None) -> dict:
    base_input = _load_json(INPUT_FILE)
    original_input = dict(base_input)
    original_output = OUTPUT_FILE.read_text(encoding="utf-8") if OUTPUT_FILE.exists() else None

    algorithm = payload.algoritmo if payload is not None else None

    options: list[dict] = []
    try:
        for scenario in OPTION_SCENARIOS:
            option_result = _run_scenario(base_input, scenario, algorithm)
            options.append(option_result)

        options = _compute_ranking(options)
        valid_options = [opt for opt in options if opt.get("status") == "ok"]
        valid_sorted = sorted(
            valid_options,
            key=lambda item: item["score"] if item.get("score") is not None else 9999,
        )

        # Regra de negocio: em "sem restricao", recomendar 1 modal vencedor
        # (cenarios *_only), evitando rota quebrada em varios modais.
        single_modal_sorted = [
            opt
            for opt in valid_sorted
            if str(opt.get("id", "")).endswith("_only")
        ]
        best_option_id = (
            single_modal_sorted[0]["id"]
            if single_modal_sorted
            else (valid_sorted[0]["id"] if valid_sorted else None)
        )

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "weights": WEIGHTS,
            "best_option_id": best_option_id,
            "options": options,
        }
    finally:
        _write_input_dict(original_input)
        if original_output is not None:
            OUTPUT_FILE.write_text(original_output, encoding="utf-8")
