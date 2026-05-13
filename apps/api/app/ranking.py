"""Score multiobjetivo (Min-Max) das opções e seleção do melhor cenário."""

from __future__ import annotations

from core.config import WEIGHTS


def _normalize(value: float, min_val: float, max_val: float) -> float:
    range_val = max_val - min_val
    if range_val == 0:
        return 0.5
    return max(0.0, min(1.0, (value - min_val) / range_val))


def compute_ranking(options: list[dict]) -> list[dict]:
    """Aplica Min-Max sobre tempo/custo/risco e atribui `score` + `rank`."""
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


def pick_best_option_id(options: list[dict]) -> str | None:
    """Regra de negócio: preferir cenários `*_only` para devolver uma rota coesa."""
    valid_sorted = sorted(
        (opt for opt in options if opt.get("status") == "ok"),
        key=lambda item: item["score"] if item.get("score") is not None else 9999,
    )
    if not valid_sorted:
        return None

    single_modal = [opt for opt in valid_sorted if str(opt.get("id", "")).endswith("_only")]
    return single_modal[0]["id"] if single_modal else valid_sorted[0]["id"]
