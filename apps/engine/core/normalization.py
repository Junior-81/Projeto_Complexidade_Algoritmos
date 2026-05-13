"""Calibração Min-Max amostrando arestas reais do grafo."""

from graph.normalizer import Normalizer
from core.config import MAX_EDGES_FOR_NORMALIZATION


def calibrate(
    graph,
    builder,
    cost_calc,
    risk_calc,
    rain_factor: float,
    tide_factor: float,
) -> dict:
    normalizer = Normalizer()
    climate_factor = rain_factor * tide_factor
    edges_seen = 0

    for _, _, edge_data in graph.edges(data=True):
        modal = str(edge_data.get("modal", "walk")).lower()
        dist = float(edge_data.get("distance_km", 0.0) or 0.0)
        if dist <= 0:
            continue

        speed = builder.get_speed(modal)
        tempo = (dist / speed) * rain_factor * tide_factor if speed > 0 else 10
        custo = cost_calc.calculate_routing_cost(
            modal,
            dist,
            time_minutes=tempo * 60,
            avg_speed_kmh=speed,
            rain_factor=rain_factor,
            tide_factor=tide_factor,
        )
        risco = risk_calc.get_adjusted_risk(modal, climate_factor) * dist / 10
        normalizer.register_values(tempo, custo, risco)

        edges_seen += 1
        if edges_seen >= MAX_EDGES_FOR_NORMALIZATION:
            break

    if edges_seen == 0:
        # Fallback defensivo: evita min=max quando o grafo não tem arestas válidas.
        for dist in (0.5, 1.0, 2.0):
            speed = builder.get_speed("walk")
            tempo = (dist / speed) * rain_factor * tide_factor if speed > 0 else 10
            custo = cost_calc.calculate_routing_cost(
                "walk",
                dist,
                time_minutes=tempo * 60,
                avg_speed_kmh=speed,
                rain_factor=rain_factor,
                tide_factor=tide_factor,
            )
            risco = risk_calc.get_adjusted_risk("walk", climate_factor) * dist / 10
            normalizer.register_values(tempo, custo, risco)

    return normalizer.normalize()
