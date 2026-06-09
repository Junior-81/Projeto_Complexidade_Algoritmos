"""Orquestracao do calculo de rota multimodal.

Esta camada decide quais algoritmos usar e monta a resposta no formato do
contrato (`edges` / `segments` / `summary` / `routePoints`):

  * **A*** (`astar_service`) para as pernas em modal continuo (acesso ao embarque
    no `initialMode` e a caminhada final), sobre a camada de rua do grafo;
  * **Dijkstra** (`dijkstra_service`) para a perna de onibus, sobre a camada GTFS.

Os pesos de cada aresta sao reais, vindos do banco (dump): velocidade do modal
(`transport_speed`), risco de crime/acidente (`crime_rate`/`accident_rate`) e
custo de combustivel/Uber/onibus (`fuel_consumption`/`uber_price_ranges`). O
grafo e construido por proximidade a partir das coordenadas reais das paradas
(ver `graph_builder`).

Edge cases do SDD continuam tratados: ponto fora da malha (400), rota inexistente
(404), timeout do calculo (408) e banco indisponivel (fallback sem 500).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.config import settings
from app.entities.db_models import (
    AccidentRate,
    CrimeRate,
    FuelConsumption,
    TransportSpeed,
    UberPriceRange,
)
from app.entities.schemas import (
    CalculateRequest,
    CalculateResponse,
    Edge,
    Segment,
    Summary,
    within_region,
)
from app.graph.cost_calculator import CostCalculator
from app.graph.geo import haversine_km
from app.graph.graph_builder import (
    GraphBuilder,
    OverlayGraph,
    build_synthetic_graph,
)
from app.graph.risk_calculator import RiskCalculator
from app.services import dijkstra_service, weights_service
from app.services.astar_service import astar

# Campos opcionais que so existem em arestas/segmentos de onibus.
_BUS_FIELDS = ("line", "gtfs_shape_id", "gtfs_validation")

# Modais de malha continua (percorrem a camada de rua via A*).
_CONTINUOUS_MODES = ("walk", "bike", "car", "moto", "uber_car", "uber_moto")

# Quanto o risco (0..1) infla o peso de busca (perna mais arriscada custa mais).
_RISK_SENSITIVITY = 0.5

# Esforco fisico relativo por km, por modal (so caminhada/bicicleta exigem).
_EFFORT_PER_KM = {"walk": 5.5, "bike": 2.5}

# Cache do grafo base (construido uma vez a partir do banco) + lock de concorrencia.
_BASE_GRAPH: GraphBuilder | None = None
_GRAPH_LOCK = threading.Lock()


class PontoForaDaMalhaError(Exception):
    """Origem ou destino fora da malha viaria mapeada (-> HTTP 400)."""


class RotaNaoEncontradaError(Exception):
    """Nao existe caminho conectando origem e destino (-> HTTP 404)."""


class CalculoTimeoutError(Exception):
    """O calculo do grafo ultrapassou o tempo maximo permitido (-> HTTP 408)."""


class _RouteContext:
    """Pesos reais carregados do banco para compor o custo das arestas."""

    def __init__(
        self,
        speeds: dict[str, float],
        cost_calc: CostCalculator,
        risk_calc: RiskCalculator,
    ) -> None:
        self.speeds = speeds
        self.cost_calc = cost_calc
        self.risk_calc = risk_calc

    def speed(self, mode: str) -> float:
        return self.speeds.get(mode, weights_service._DEFAULT_SPEED_KMH.get(mode, 30.0))


def calculate(req: CalculateRequest, session: Session) -> CalculateResponse:
    """Calcula a rota multimodal entre `origin` e `destination`.

    A construcao do grafo e a leitura dos pesos acontecem fora do timeout (sao
    I/O de banco); apenas a busca (A*/Dijkstra) roda no worker com limite de
    tempo, isolando o edge case de calculo longo.
    """
    if not within_region(req.origin):
        raise PontoForaDaMalhaError("Origin point is outside the road network")
    if not within_region(req.destination):
        raise PontoForaDaMalhaError("Destination point is outside the road network")

    # Grafo (cacheado) e pesos do banco; ambos degradam para fallback se o banco
    # estiver indisponivel, evitando 500.
    base = _get_base_graph(session) or build_synthetic_graph(req.origin, req.destination)
    ctx = _load_context(session)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_compute_route, req, base, ctx)
        try:
            return future.result(timeout=settings.graph_timeout_seconds)
        except FutureTimeoutError as exc:
            raise CalculoTimeoutError(
                "Route calculation exceeded the maximum allowed time"
            ) from exc


# ---------------------------------------------------------------------------
# Grafo base (cache) e contexto de pesos
# ---------------------------------------------------------------------------


def _get_base_graph(session: Session) -> GraphBuilder | None:
    """Constroi (uma vez) o grafo de proximidade a partir das paradas do banco.

    Retorna None se o banco estiver indisponivel/vazio, sinalizando ao chamador
    para usar o grafo sintetico de contingencia.
    """
    global _BASE_GRAPH
    if _BASE_GRAPH is not None:
        return _BASE_GRAPH
    with _GRAPH_LOCK:
        if _BASE_GRAPH is not None:
            return _BASE_GRAPH
        try:
            builder = GraphBuilder().build_from_session(session)
        except SQLAlchemyError:
            return None
        if not builder.nodes:
            return None
        _BASE_GRAPH = builder
        return _BASE_GRAPH


def _load_context(session: Session) -> _RouteContext:
    """Carrega velocidades, custo e risco do banco; usa defaults se indisponivel."""
    speeds = dict(weights_service._DEFAULT_SPEED_KMH)
    fuel_by_mode: dict[str, dict[str, float]] = {}
    uber_config: dict[str, dict[str, float]] = {}
    crime_by_mode: dict[str, int] = {}
    accident_by_mode: dict[str, tuple[int, int]] = {}

    try:
        for row in session.exec(select(TransportSpeed)).all():
            speeds[row.mode] = row.speed_kmh
        for row in session.exec(select(FuelConsumption)).all():
            fuel_by_mode[row.mode] = {
                "km_per_liter": row.km_per_liter,
                "fixed_cost_per_km": row.fixed_cost_per_km,
            }
        for row in session.exec(select(UberPriceRange)).all():
            uber_config[row.service] = {
                "base_fare": row.base_fare,
                "km_min": row.km_min,
                "km_max": row.km_max,
                "min_min": row.min_min,
                "min_max": row.min_max,
            }
        for row in session.exec(select(CrimeRate)).all():
            crime_by_mode[row.mode] = row.robberies
        for row in session.exec(select(AccidentRate)).all():
            accident_by_mode[row.mode] = (row.deaths, row.involved)
    except SQLAlchemyError:
        # Banco fora do ar: segue com pesos neutros/default (sem 500).
        pass

    return _RouteContext(
        speeds=speeds,
        cost_calc=CostCalculator(fuel_by_mode=fuel_by_mode, uber_config=uber_config),
        risk_calc=RiskCalculator(
            crime_by_mode=crime_by_mode, accident_by_mode=accident_by_mode
        ),
    )


# ---------------------------------------------------------------------------
# Calculo da rota (A* + Dijkstra)
# ---------------------------------------------------------------------------


def _compute_route(
    req: CalculateRequest, base: GraphBuilder, ctx: _RouteContext
) -> CalculateResponse:
    """Produz a rota: acesso (A*) -> onibus (Dijkstra) -> caminhada final (A*)."""
    origin, destination = req.origin, req.destination
    board = base.nearest_stop(origin)
    alight = base.nearest_stop(destination)
    if board is None or alight is None:
        raise RotaNaoEncontradaError("Route not found")

    # Overlay liga origem/destino as paradas vizinhas sem mutar o grafo base.
    overlay = OverlayGraph(
        base,
        base.make_access_edges(origin, ("street", "bus")),
        base.make_access_edges(destination, ("street", "bus")),
    )

    access_mode = req.initial_mode if req.initial_mode in _CONTINUOUS_MODES else "walk"

    leg_access = _astar_leg(overlay, origin, board, access_mode, ctx)
    leg_bus = _bus_leg(base, board, alight, ctx)
    leg_walk = _astar_leg(overlay, alight, destination, "walk", ctx)

    path = leg_access + leg_bus + leg_walk
    # Arestas granulares (rua a rua): base de TODO o calculo (totais e medias).
    granular = _edges_from_path(path, access_mode, ctx)
    if not granular:
        raise RotaNaoEncontradaError("Route not found")

    # segments / summary / routePoints derivam das granulares -> calculo inalterado.
    segments = _group_segments(granular)
    summary = _build_summary(granular, segments)
    route_points = _build_route_points(granular)
    # O campo `edges` colapsa trechos do mesmo modal: 1 item por troca de modal.
    edges = _collapse_edges(granular)
    return CalculateResponse(
        edges=edges, segments=segments, summary=summary, route_points=route_points
    )


def _astar_leg(
    graph: Any, origem: tuple, destino: tuple, mode: str, ctx: _RouteContext
) -> list[dict[str, Any]]:
    """Roda o A* numa perna de modal continuo, anotando o modal em cada aresta."""
    if origem == destino:
        return []
    speed = ctx.speed(mode)

    def weight_fn(edge: dict[str, Any]) -> float:
        return _search_weight(mode, edge["distance"], ctx)

    def heuristica(no: tuple, goal: tuple) -> float:
        # Limite inferior admissivel: tempo em linha reta na velocidade do modal.
        return haversine_km(no, goal) / speed

    path = astar(
        graph,
        origem,
        destino,
        weight_fn,
        heuristica,
        edge_filter=lambda e: e["kind"] == "street",
    )
    for edge in path:
        edge["leg_mode"] = mode
    return path


def _bus_leg(
    base: GraphBuilder, board: tuple, alight: tuple, ctx: _RouteContext
) -> list[dict[str, Any]]:
    """Roda o Dijkstra na rede de onibus; garante ao menos uma aresta de onibus.

    Se nao houver caminho de onibus conectando embarque e desembarque (rede de
    proximidade desconexa para pontos distantes), sintetiza uma aresta direta
    para manter o trecho multimodal coerente.
    """
    if board != alight:
        path = dijkstra_service.dijkstra(
            base,
            board,
            alight,
            weight_fn=lambda e: _search_weight("bus", e["distance"], ctx),
            edge_filter=lambda e: e["kind"] == "bus",
        )
        if path:
            for edge in path:
                edge["leg_mode"] = "bus"
            return path

    if board == alight:
        return []

    # Fallback: aresta de onibus direta (rede GTFS aproximada).
    line, shape_id = base._bus_metadata(board, alight)
    return [
        {
            "from": board,
            "to": alight,
            "distance": haversine_km(board, alight),
            "geometry": [[board[0], board[1]], [alight[0], alight[1]]],
            "kind": "bus",
            "line": line,
            "shape_id": shape_id,
            "leg_mode": "bus",
        }
    ]


# ---------------------------------------------------------------------------
# Metricas por aresta (peso de busca + campos do schema)
# ---------------------------------------------------------------------------


def _search_weight(mode: str, distance_km: float, ctx: _RouteContext) -> float:
    """Custo de busca de uma aresta: tempo inflado pela intensidade de risco."""
    time_h = distance_km / ctx.speed(mode)
    risk = ctx.risk_calc.risk_intensity(mode)
    return time_h * (1 + _RISK_SENSITIVITY * risk)


def _edges_from_path(
    path: list[dict[str, Any]], access_mode: str, ctx: _RouteContext
) -> list[Edge]:
    """Converte as arestas internas do caminho em `Edge` do contrato."""
    edges: list[Edge] = []
    bus_fare_charged = False
    for raw in path:
        mode = raw.get("leg_mode", access_mode)
        distance = raw["distance"]
        speed = ctx.speed(mode)
        time_h = distance / speed
        duration_min = time_h * 60
        risk = ctx.risk_calc.risk_for_mode(mode, distance)
        effort = _EFFORT_PER_KM.get(mode, 0.0) * distance
        cost = ctx.cost_calc.cost_for_mode(mode, distance, duration_min)

        is_bus = raw["kind"] == "bus"
        if is_bus and not bus_fare_charged:
            cost += ctx.cost_calc.bus_boarding_fare()
            bus_fare_charged = True

        weight = _search_weight(mode, distance, ctx)
        edge = Edge(
            mode=mode,
            means=mode,
            origin=tuple(raw["from"]),
            destination=tuple(raw["to"]),
            distance=round(distance, 4),
            time=round(time_h, 4),
            cost=round(cost, 4),
            effort=round(effort, 4),
            risk=round(risk, 4),
            weight=round(weight, 4),
            average_speed_kmh=round(speed, 2),
            geometry=raw["geometry"],
        )
        if is_bus:
            edge.line = raw.get("line")
            edge.gtfs_shape_id = raw.get("shape_id")
            edge.gtfs_validation = True
        edges.append(edge)
    return edges


def _collapse_edges(edges: list[Edge]) -> list[Edge]:
    """Mescla arestas consecutivas de mesmo modal em uma unica `Edge`.

    Apenas formatacao da saida: o campo `edges` passa a trazer um item por trecho
    de modal (so muda quando ha troca de modal), preservando a geometria completa
    para plotagem. Nao altera nenhum calculo — `segments`, `summary` e
    `routePoints` continuam derivados das arestas granulares.
    """
    merged: list[Edge] = []
    for edge in edges:
        if merged and merged[-1].mode == edge.mode:
            merged[-1] = _merge_pair(merged[-1], edge)
        else:
            # Copia para nao mutar a aresta granular original.
            merged.append(edge.model_copy(deep=True))
    return merged


def _merge_pair(acc: Edge, nxt: Edge) -> Edge:
    """Funde duas arestas de mesmo modal somando totais e concatenando geometria."""
    geometry = list(acc.geometry)
    for point in nxt.geometry:
        if not geometry or geometry[-1] != point:
            geometry.append(list(point))

    distance = acc.distance + nxt.distance
    time = acc.time + nxt.time
    return acc.model_copy(
        update={
            "destination": nxt.destination,
            "distance": round(distance, 4),
            "time": round(time, 4),
            "cost": round(acc.cost + nxt.cost, 4),
            "effort": round(acc.effort + nxt.effort, 4),
            "risk": round(acc.risk + nxt.risk, 4),
            "weight": round(acc.weight + nxt.weight, 4),
            "average_speed_kmh": round(distance / time, 2) if time else acc.average_speed_kmh,
            "geometry": geometry,
        }
    )


# ---------------------------------------------------------------------------
# Montagem de segments / summary / routePoints (agrupamento generico)
# ---------------------------------------------------------------------------


def _group_segments(edges: list[Edge]) -> list[Segment]:
    """Agrupa edges consecutivas por modal, somando os totais de cada trecho."""
    segments: list[Segment] = []
    group: list[Edge] = []

    def close_group(group: list[Edge]) -> Segment:
        first, last = group[0], group[-1]
        time = sum(e.time for e in group)
        distance = sum(e.distance for e in group)
        cost = sum(e.cost for e in group)
        effort = sum(e.effort for e in group)
        average_risk = sum(e.risk for e in group) / len(group)
        hours = sum(e.time for e in group)
        average_speed = round(distance / hours, 2) if hours else 0.0

        seg = Segment(
            mode=first.mode,
            means=first.means,
            origin=first.origin,
            destination=last.destination,
            time=round(time, 4),
            distance=round(distance, 4),
            cost=round(cost, 4),
            effort=round(effort, 4),
            average_risk=round(average_risk, 4),
            average_speed_kmh=average_speed,
            edge_count=len(group),
        )
        if first.mode == "bus":
            for field in _BUS_FIELDS:
                setattr(seg, field, getattr(first, field))
        return seg

    for edge in edges:
        if group and edge.mode != group[-1].mode:
            segments.append(close_group(group))
            group = []
        group.append(edge)
    if group:
        segments.append(close_group(group))

    return segments


def _build_summary(edges: list[Edge], segments: list[Segment]) -> Summary:
    """Calcula os totais gerais da viagem."""
    total_time = sum(e.time for e in edges)
    total_distance = sum(e.distance for e in edges)
    average_risk = sum(e.risk for e in edges) / len(edges) if edges else 0.0
    average_speed = round(total_distance / total_time, 2) if total_time else 0.0

    return Summary(
        total_time=round(total_time, 4),
        total_cost=round(sum(e.cost for e in edges), 4),
        total_effort=round(sum(e.effort for e in edges), 4),
        total_distance=round(total_distance, 4),
        average_risk=round(average_risk, 4),
        total_average_speed=average_speed,
    )


def _build_route_points(edges: list[Edge]) -> list[list[float]]:
    """Concatena a geometria das arestas numa sequencia de coordenadas."""
    points: list[list[float]] = []
    for edge in edges:
        for point in edge.geometry:
            if not points or points[-1] != point:
                points.append(list(point))
    return points
