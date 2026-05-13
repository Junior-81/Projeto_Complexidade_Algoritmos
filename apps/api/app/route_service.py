"""Camada de serviço: orquestra chamadas ao engine e monta respostas."""

from __future__ import annotations

from datetime import datetime

from core.config import WEIGHTS
from core.pipeline import RouteError, run_route

from app.ranking import compute_ranking, pick_best_option_id
from app.scenarios import OPTION_SCENARIOS


def run_scenario(base_input: dict, scenario: dict, algorithm: str | None) -> dict:
    """Executa o engine para um cenário e formata o resultado (ou erro)."""
    scenario_input = dict(base_input)
    scenario_input["modo_inicial"] = scenario["modo_inicial"]
    if algorithm:
        scenario_input["algoritmo"] = algorithm

    restricao_modal = scenario.get("restricao_modal")
    if restricao_modal:
        scenario_input["restricao_modal"] = restricao_modal
    else:
        scenario_input.pop("restricao_modal", None)

    base_meta = {
        "id": scenario["id"],
        "label": scenario["label"],
        "modo_inicial": scenario["modo_inicial"],
        "restricao_modal": restricao_modal,
    }

    try:
        route_data = run_route(scenario_input)
    except RouteError as exc:
        return {**base_meta, "status": "error", "error": {"message": str(exc)}}

    return {
        **base_meta,
        "status": "ok",
        "resumo": route_data.get("resumo", {}),
        "segments_count": len(route_data.get("segments", [])),
        "edges_count": len(route_data.get("edges", [])),
        "route": route_data,
    }


def build_options_response(base_input: dict, algorithm: str | None) -> dict:
    """Roda todos os cenários, calcula ranking e devolve o payload final."""
    options = [run_scenario(base_input, sc, algorithm) for sc in OPTION_SCENARIOS]
    options = compute_ranking(options)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "weights": WEIGHTS,
        "best_option_id": pick_best_option_id(options),
        "options": options,
    }
