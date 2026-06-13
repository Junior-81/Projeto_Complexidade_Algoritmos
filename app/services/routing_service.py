import logging
import threading

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from sqlmodel import Session
from app.config import settings
from app.graph.cost_calculator import CostCalculator
from app.graph.graph_builder import GraphBuilder
from app.graph.normalizer import Normalizer
from app.graph.risk_calculator import RiskCalculator
from app.services.astar_service import AStarMultimodal
from app.services.dijkstra_service import DijkstraMultimodal
from app.services import weather
from app.services.factors import (
    load_bus_network,
    load_factor_frames,
    load_weather_factors,
)
from app.services.path_reconstructor import PathReconstructor
from app.entities.schemas import (
    CalculateRequest,
    CalculateResponse,
    Edge,
    Segment,
    Summary,
    within_region,
)

logger = logging.getLogger(__name__)
GASOLINE_PRICE_PER_LITER = 7.50
RECIFE_LOCATION = "Recife, Brazil"

_NORM_SAMPLE_EDGES = 80000
_engine: dict | None = None
_engine_lock = threading.Lock()


class PontoForaDaMalhaError(Exception):
    """Origem ou destino fora da malha viaria mapeada (-> HTTP 400)."""


class RotaNaoEncontradaError(Exception):
    """Nao existe caminho conectando origem e destino (-> HTTP 404)."""


class CalculoTimeoutError(Exception):
    """O calculo do grafo ultrapassou o tempo maximo permitido (-> HTTP 408)."""

def _compute_norm_params(graph, builder, cost_calc, risk_calc) -> dict:
    """Amostra a distribuicao real do grafo para os parametros de Min-Max."""
    normalizer = Normalizer()
    seen = 0
    for _, _, edge_data in graph.edges(data=True):
        modal = str(edge_data.get("modal", "walk")).lower()
        dist = float(edge_data.get("distance_km", 0.0) or 0.0)
        if dist <= 0:
            continue
        speed = builder.get_speed(modal)
        tempo = (dist / speed) if speed > 0 else 10
        custo = cost_calc.calculate_routing_cost(
            modal, dist, time_minutes=tempo * 60, avg_speed_kmh=speed,
            rain_factor=1.0, tide_factor=1.0,
        )
        risco = risk_calc.get_adjusted_risk(modal, 1.0) * dist / 10
        normalizer.register_values(tempo, custo, risco)
        seen += 1
        if seen >= _NORM_SAMPLE_EDGES:
            break

    if seen == 0:
        # Fallback defensivo: evita min == max quando nao ha arestas validas.
        for dist in (0.5, 1.0, 2.0):
            speed = builder.get_speed("walk")
            tempo = (dist / speed) if speed > 0 else 10
            custo = cost_calc.calculate_routing_cost(
                "walk", dist, time_minutes=tempo * 60, avg_speed_kmh=speed,
            )
            risco = risk_calc.get_adjusted_risk("walk", 1.0) * dist / 10
            normalizer.register_values(tempo, custo, risco)

    return normalizer.normalize()


def _build_engine(session: Session) -> dict:
    """Constroi o engine: fatores do DB, grafo OSMnx e parametros de normalizacao."""
    logger.info("Inicializando engine de roteamento (primeira chamada)...")
    frames = load_factor_frames(session)

    cost_calc = CostCalculator(
        frames["fuel"], frames["uber"], frames["speed"],
        gas_price=GASOLINE_PRICE_PER_LITER,
    )
    risk_calc = RiskCalculator(frames["crime"], frames["accident"])

    builder = GraphBuilder(RECIFE_LOCATION)
    builder.load_base_graph()
    bus_network = load_bus_network(session)
    graph = builder.build_multimodal_graph(bus_network=bus_network)
    builder.load_speed_data(frames["speed"])

    norm_params = _compute_norm_params(graph, builder, cost_calc, risk_calc)
    weather_map = load_weather_factors(session)
    logger.info("Engine de roteamento pronto.")

    return {
        "builder": builder,
        "graph": graph,
        "cost_calc": cost_calc,
        "risk_calc": risk_calc,
        "norm_params": norm_params,
        "weather_map": weather_map,
    }


def _resolve_base_rain(req: CalculateRequest, engine: dict) -> float:
    """Fator base de chuva: usa o override `weather` da requisicao, senao consulta
    a Open-Meteo pela origem. Converte a condicao no fator via weather_map (DB).
    """
    weather_map: dict[str, float] = engine.get("weather_map", {})
    condition = req.weather or weather.get_condition(req.origin[0], req.origin[1])
    factor = weather_map.get(condition, 1.0)
    logger.info("Clima: condicao=%s -> fator base=%.2f", condition, factor)
    return factor


def _get_engine(session: Session) -> dict:
    """Devolve o engine, construindo-o sob demanda (thread-safe, uma vez so)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = _build_engine(session)
    return _engine

def calculate(req: CalculateRequest, session: Session) -> CalculateResponse:
    """Calcula a rota multimodal entre `origin` e `destination`.

    Casos de borda:
      * origem/destino fora da regiao -> PontoForaDaMalhaError (400);
      * ausencia de caminho           -> RotaNaoEncontradaError (404);
      * busca > GRAPH_TIMEOUT         -> CalculoTimeoutError (408);
      * banco indisponivel            -> fatores default (tratado em factors).
    """
    if not within_region(req.origin):
        raise PontoForaDaMalhaError("Origin point is outside the road network")
    if not within_region(req.destination):
        raise PontoForaDaMalhaError("Destination point is outside the road network")

    # Build do grafo (potencialmente lento na 1a vez) fica FORA do timeout.
    engine = _get_engine(session)
    # Clima tambem fora do timeout (chamada externa curta + cache TTL).
    base_rain = _resolve_base_rain(req, engine)
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_compute_route, req, engine, base_rain)

    try:
        return future.result(timeout=settings.graph_timeout_seconds)
    except FutureTimeoutError as exc:
        raise CalculoTimeoutError(
            "Route calculation exceeded the maximum allowed time"
        ) from exc
    finally:
        executor.shutdown(wait=False)


_VEHICLE_MODES = {"car", "moto", "bike", "uber_car", "uber_moto"}

# Penaliza trechos a pe no modo onibus para desencorajar "andar a viagem toda"
# em vez de pegar o onibus (mesmo valor da branch refactor).
_BUS_WALK_PENALTY = 1.4
# Custo fixo somado a cada EMBARQUE (transicao nao-onibus -> onibus). Os pesos
# por aresta sao da ordem de 0.001-0.004, entao 0.05 torna um 2o embarque
# claramente pior que um -> o algoritmo embarca uma vez e fica no onibus.
_BUS_BOARDING_PENALTY = 0.05


class _SearchConfig:
    """Parametros de busca derivados do modal de entrada."""

    def __init__(self, start_mode, allowed_modes, bus_required=False,
                 max_walk_km=None, walk_penalty=1.0, boarding_penalty=0.0):
        self.start_mode = start_mode
        self.allowed_modes = allowed_modes
        self.bus_required = bus_required
        self.max_walk_km = max_walk_km
        self.walk_penalty = walk_penalty
        self.boarding_penalty = boarding_penalty


def _resolve_modes(initial_mode: str) -> _SearchConfig:
    """Mapeia o modal de entrada para a configuracao de busca.

    - veiculo proprio (car/moto/bike/uber): viagem inteira nesse modal;
    - walk: rota so a pe;
    - bus: multimodal {walk, bus} com obrigatoriedade de usar onibus
      (bus_required) e penalidade de caminhada -> mescla walk + bus.
    """
    if initial_mode in _VEHICLE_MODES:
        return _SearchConfig(initial_mode, {initial_mode})
    if initial_mode == "bus":
        return _SearchConfig(
            "walk", {"walk", "bus"}, bus_required=True,
            walk_penalty=_BUS_WALK_PENALTY,
            boarding_penalty=_BUS_BOARDING_PENALTY,
        )
    return _SearchConfig("walk", {"walk"})


# Modais comparados no modo "auto" (cada um vira um candidato; o melhor vence).
_AUTO_CANDIDATES = ["walk", "bike", "car", "moto", "uber_car", "uber_moto", "bus"]


def _route_for_mode(
    engine: dict, start_node, goal_node, mode: str, base_rain: float = 1.0
) -> dict | None:
    """Roda a busca de UM modal e devolve o resultado reconstruido (chaves PT).

    A chuva entra como `rain_factor` EFETIVO do modal: modos expostos (walk/bike/
    moto/uber_moto) sofrem o fator cheio; protegidos (car/uber_car/bus) sofrem
    menos. Devolve None se nao houver caminho viavel.
    """
    graph = engine["graph"]
    cost_calc = engine["cost_calc"]
    risk_calc = engine["risk_calc"]
    norm_params = engine["norm_params"]
    builder: GraphBuilder = engine["builder"]

    cfg = _resolve_modes(mode)
    # Fator de chuva sensivel ao modal (no bus, o trecho a pe de acesso usa o
    # fator do onibus -> aproximacao aceitavel, pois o acesso e curto).
    rain = weather.effective_rain(mode, base_rain)

    # Multimodal (bus) -> Dijkstra (otimo); modal unico -> A* (guloso e rapido).
    algo_cls = DijkstraMultimodal if cfg.bus_required else AStarMultimodal
    path = algo_cls(graph, norm_params).search(
        (start_node, cfg.start_mode),
        (goal_node, cfg.start_mode),
        cost_calc,
        risk_calc,
        rain_factor=rain,
        tide_factor=1.0,
        speed_getter=builder.get_speed,
        start_modal=cfg.start_mode,
        allowed_modes=cfg.allowed_modes,
        bus_required=cfg.bus_required,
        max_walk_distance_km=cfg.max_walk_km,
        walk_penalty_factor=cfg.walk_penalty,
        boarding_penalty=cfg.boarding_penalty,
    )
    if not path:
        return None

    result = PathReconstructor(
        graph, cost_calc, risk_calc, norm_params,
        rain_factor=rain, tide_factor=1.0, speed_data=builder.speed_data,
    ).reconstruct_route(path)

    return result if result["edges"] else None


def _normalize(values: list[float]) -> list[float]:
    """Min-Max para [0,1]; se todos iguais, devolve 0 (nao desempata)."""
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return [0.0 for _ in values]
    return [(v - lo) / span for v in values]


def _pick_best(candidates: list[tuple[str, dict]]) -> tuple[str, dict]:
    """Escolhe o melhor candidato por custo-beneficio-tempo.

    Score = 0.5*tempo + 0.3*custo + 0.2*risco (cada metrica normalizada entre os
    candidatos). O 'custo' ja embute o esforco fisico (calculate_routing_cost).
    Menor score vence.
    """
    resumos = [r["resumo"] for _, r in candidates]
    t = _normalize([x["tempo_total"] for x in resumos])
    c = _normalize([x["custo_total"] for x in resumos])
    risk = _normalize([x["risco_medio"] for x in resumos])
    scores = [0.5 * t[i] + 0.3 * c[i] + 0.2 * risk[i] for i in range(len(candidates))]
    best_idx = min(range(len(candidates)), key=lambda i: scores[i])
    return candidates[best_idx]


def _compute_route(
    req: CalculateRequest, engine: dict, base_rain: float = 1.0
) -> CalculateResponse:
    """Reconstroi a rota no contrato da API. Modo 'auto' compara todos os modais."""
    builder: GraphBuilder = engine["builder"]
    start_node = builder.nearest_node(req.origin[0], req.origin[1])
    goal_node = builder.nearest_node(req.destination[0], req.destination[1])

    if req.initial_mode == "auto":
        candidates: list[tuple[str, dict]] = []
        for mode in _AUTO_CANDIDATES:
            result = _route_for_mode(engine, start_node, goal_node, mode, base_rain)
            if result is not None:
                candidates.append((mode, result))
        if not candidates:
            raise RotaNaoEncontradaError("Route not found")
        chosen_mode, best = _pick_best(candidates)
        logger.info(
            "auto: %d candidatos -> escolhido '%s'",
            len(candidates), chosen_mode,
        )
        return _to_response(best, chosen_mode=chosen_mode)

    result = _route_for_mode(engine, start_node, goal_node, req.initial_mode, base_rain)
    if result is None:
        raise RotaNaoEncontradaError("Route not found")
    return _to_response(result, chosen_mode=req.initial_mode)


def _to_response(result: dict, chosen_mode: str | None = None) -> CalculateResponse:
    edges = [_map_edge(e) for e in result["edges"]]
    segments = [_map_segment(s) for s in result["segments"]]
    summary = _map_summary(result["resumo"])
    return CalculateResponse(
        edges=edges,
        segments=segments,
        summary=summary,
        route_points=_route_points(edges),
        chosen_mode=chosen_mode,
    )


def _map_edge(e: dict) -> Edge:
    origin = (float(e["origem"][0]), float(e["origem"][1]))
    destination = (float(e["destino"][0]), float(e["destino"][1]))
    return Edge(
        mode=e["modo"],
        means=e.get("meio", e["modo"]),
        origin=origin,
        destination=destination,
        distance=e["distancia"],
        time=e["tempo"],
        cost=e["custo"],
        effort=e["esforco"],
        risk=e["risco"],
        weight=e["peso"],
        average_speed_kmh=e["velocidade_media_kmh"],
        geometry=[[origin[0], origin[1]], [destination[0], destination[1]]],
        line=e.get("linha"),
        gtfs_shape_id=e.get("gtfs_shape_id"),
        gtfs_validation=e.get("validacao_gtfs"),
    )


def _map_segment(s: dict) -> Segment:
    return Segment(
        mode=s["modo"],
        means=s.get("meio", s["modo"]),
        origin=(float(s["origem"][0]), float(s["origem"][1])),
        destination=(float(s["destino"][0]), float(s["destino"][1])),
        time=s["tempo"],
        distance=s["distancia"],
        cost=s["custo"],
        effort=s["esforco"],
        average_risk=s["risco_medio"],
        average_speed_kmh=s["velocidade_media_kmh"],
        edge_count=s["quantidade_arestas"],
        line=s.get("linha"),
        gtfs_shape_id=s.get("gtfs_shape_id"),
        gtfs_validation=s.get("validacao_gtfs"),
    )


def _map_summary(r: dict) -> Summary:
    return Summary(
        total_time=r["tempo_total"],
        total_cost=r["custo_total"],
        total_effort=r["esforco_total"],
        total_distance=r["distancia_total"],
        average_risk=r["risco_medio"],
        total_average_speed=r["velocidade_media_total"],
    )


def _route_points(edges: list[Edge]) -> list[list[float]]:
    """Concatena a geometria das arestas numa sequencia de coordenadas."""
    points: list[list[float]] = []
    for edge in edges:
        for point in edge.geometry:
            if not points or points[-1] != point:
                points.append(list(point))
    return points
