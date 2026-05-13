"""Pipeline de roteamento multimodal — função pura, importável.

`run_route(input_data)` recebe um dicionário no formato de `input.json` e
retorna o dicionário no formato de `output.json`. Não faz I/O de arquivo.
"""

from __future__ import annotations

import logging
from typing import Any

from loaders.csv_loader import CSVLoader
from loaders.weather_api import WeatherAPI
from graph.graph_builder import GraphBuilder
from graph.risk_calculator import RiskCalculator
from graph.cost_calculator import CostCalculator
from routing.astar_multimodal import AStarMultimodal
from routing.dijkstra_multimodal import DijkstraMultimodal
from routing.path_reconstructor import PathReconstructor

from core.config import (
    DATA_DIR,
    DEFAULT_ALGORITHM,
    GASOLINE_PRICE_PER_LITER,
    GTFS_DIR,
    OSMNX_PLACE,
    VALID_ALGORITHMS,
)
from core.restrictions import parse as parse_restriction
from core.normalization import calibrate as calibrate_norm

log = logging.getLogger(__name__)


class RouteError(RuntimeError):
    """Erro recuperável do pipeline (input inválido, sem rota, etc.)."""


def _find_nearest_node(graph, lat: float, lon: float):
    import osmnx as ox

    try:
        return ox.distance.nearest_nodes(graph, lon, lat)
    except Exception:
        min_dist = float("inf")
        nearest = None
        for node, data in graph.nodes(data=True):
            node_lat = data.get("y", 0)
            node_lon = data.get("x", 0)
            dist = (node_lat - lat) ** 2 + (node_lon - lon) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = node
        return nearest


def run_route(input_data: dict[str, Any]) -> dict[str, Any]:
    """Executa o pipeline de roteamento e retorna o resultado.

    Levanta `RouteError` em caso de entrada inválida ou rota inexistente.
    """

    # 1. Parse de input
    try:
        origem_lat, origem_lon = input_data["origem"]
        destino_lat, destino_lon = input_data["destino"]
        modo_inicial = input_data["modo_inicial"].lower()
    except (KeyError, TypeError, ValueError) as e:
        raise RouteError(f"input inválido: {e}") from e

    algoritmo = str(input_data.get("algoritmo", DEFAULT_ALGORITHM)).lower()
    if algoritmo not in VALID_ALGORITHMS:
        log.warning("Algoritmo '%s' inválido. Usando %s.", algoritmo, DEFAULT_ALGORITHM)
        algoritmo = DEFAULT_ALGORITHM

    restriction = parse_restriction(input_data.get("restricao_modal"))
    if restriction.allowed_modes:
        log.info("Restrição modal: %s", sorted(restriction.allowed_modes))

    # 2. CSVs
    loader = CSVLoader(str(DATA_DIR))
    data = loader.load_all()

    # 3. Riscos
    risk_calc = RiskCalculator(data.get("crime_rate"), data.get("accident_rate"))

    # 4. Custos e velocidades
    cost_calc = CostCalculator(
        data.get("fuel_consumption"),
        data.get("uber_prices"),
        data.get("transport_speed"),
        gas_price=GASOLINE_PRICE_PER_LITER,
    )

    # 5. Clima
    weather_api = WeatherAPI()
    weather = weather_api.get_weather(origem_lat, origem_lon)
    rain_factor = weather.get("rain_factor", 1.0)
    tide_factor = weather_api.get_tide_factor(origem_lat, origem_lon)
    log.info(
        "Clima: %.1fmm | rain=%.2f tide=%.2f",
        weather.get("precipitation", 0),
        rain_factor,
        tide_factor,
    )

    # 6. Grafo multimodal (com cache)
    builder = GraphBuilder(OSMNX_PLACE)
    cached = GraphBuilder.load_graph_cache()
    if cached:
        graph, builder.speed_data = cached
        builder.load_base_graph()
        builder.load_flood_data(data.get("flood_risk"))
    else:
        builder.load_base_graph()
        builder.load_speed_data(data.get("transport_speed"))
        builder.load_flood_data(data.get("flood_risk"))
        graph = builder.build_multimodal_graph()
        builder.add_gtfs_bus_routes(str(GTFS_DIR))
        GraphBuilder.save_graph_cache(graph, builder.speed_data)

    if graph is None:
        raise RouteError("falha ao construir grafo")
    builder.multimodal_graph = graph

    # 7. Nós de origem/destino
    start_node = _find_nearest_node(builder.base_graph, origem_lat, origem_lon)
    goal_node = _find_nearest_node(builder.base_graph, destino_lat, destino_lon)

    # 8. Normalização
    norm_params = calibrate_norm(
        graph, builder, cost_calc, risk_calc, rain_factor, tide_factor
    )

    # 9. Busca
    start_state = (start_node, modo_inicial)
    goal_state = (goal_node, modo_inicial)
    speed_getter = lambda m: builder.get_speed(m)

    search_kwargs = dict(
        cost_calc=cost_calc,
        risk_calc=risk_calc,
        rain_factor=rain_factor,
        tide_factor=tide_factor,
        speed_getter=speed_getter,
        start_modal=modo_inicial,
        allowed_modes=restriction.allowed_modes,
        bus_required=restriction.bus_required,
        max_walk_distance_km=restriction.max_walk_distance_km,
        walk_penalty_factor=restriction.walk_penalty_factor,
    )

    if algoritmo == "astar":
        searcher = AStarMultimodal(graph, norm_params)
    else:
        searcher = DijkstraMultimodal(graph, norm_params)

    path = searcher.search(start_state, goal_state, **search_kwargs)

    if path is None:
        raise RouteError("nenhuma rota encontrada")

    # 10. Reconstrução
    reconstructor = PathReconstructor(
        graph,
        cost_calc,
        risk_calc,
        norm_params,
        rain_factor=rain_factor,
        tide_factor=tide_factor,
        speed_data=builder.speed_data,
    )
    return reconstructor.reconstruct_route(path)
