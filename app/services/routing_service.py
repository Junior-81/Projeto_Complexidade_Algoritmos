"""Orquestracao do calculo de rota multimodal.

Esta camada decide quais algoritmos usar (A* para malha continua, Dijkstra para
GTFS), aplica os pesos dinamicos via `weights_service` e monta a resposta no
formato do contrato (`edges` / `segments` / `summary` / `routePoints`).

Nesta fase de setup, o calculo retorna um **mock estruturado** com o formato
exato esperado, montado pelos helpers `_group_segments` e `_build_summary`, ja
deixando o pipeline pronto para receber a implementacao real dos algoritmos.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from sqlmodel import Session

from app.config import settings
from app.entities.schemas import (
    CalculateRequest,
    CalculateResponse,
    Edge,
    Segment,
    Summary,
    within_region,
)

# Campos opcionais que so existem em arestas/segmentos de onibus.
_BUS_FIELDS = ("line", "gtfs_shape_id", "gtfs_validation")


class PontoForaDaMalhaError(Exception):
    """Origem ou destino fora da malha viaria mapeada (-> HTTP 400)."""


class RotaNaoEncontradaError(Exception):
    """Nao existe caminho conectando origem e destino (-> HTTP 404)."""


class CalculoTimeoutError(Exception):
    """O calculo do grafo ultrapassou o tempo maximo permitido (-> HTTP 408)."""


def calculate(req: CalculateRequest, session: Session) -> CalculateResponse:
    """Calcula a rota multimodal entre `origin` e `destination`.

    Trata os casos de borda do SDD:
      * origem/destino fora da regiao -> PontoForaDaMalhaError (400);
      * ausencia de caminho           -> RotaNaoEncontradaError (404);
      * calculo > GRAPH_TIMEOUT       -> CalculoTimeoutError (408);
      * banco indisponivel            -> pesos neutros (tratado em weights_service).
    """
    # Edge case: coordenada isolada (oceano, rio, fora da malha) -> 400.
    if not within_region(req.origin):
        raise PontoForaDaMalhaError("Origin point is outside the road network")
    if not within_region(req.destination):
        raise PontoForaDaMalhaError("Destination point is outside the road network")

    # Edge case: timeout. O calculo (futuramente pesado) roda num worker e e
    # interrompido logicamente se ultrapassar GRAPH_TIMEOUT_SECONDS.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_compute_route, req, session)
        try:
            return future.result(timeout=settings.graph_timeout_seconds)
        except FutureTimeoutError as exc:
            raise CalculoTimeoutError(
                "Route calculation exceeded the maximum allowed time"
            ) from exc


def _compute_route(req: CalculateRequest, session: Session) -> CalculateResponse:
    """Produz a rota propriamente dita.

    MOCK: retorna um conjunto representativo de arestas com o formato exato de
    saida. A implementacao real chamara `astar`/`dijkstra` sobre o grafo,
    aplicando os multiplicadores de `weights_service.get_edge_multipliers`.
    """
    edges = _mock_edges(req)
    if not edges:
        # Edge case: inviabilidade modal -> 404.
        raise RotaNaoEncontradaError("Route not found")

    segments = _group_segments(edges)
    summary = _build_summary(edges, segments)
    route_points = _build_route_points(edges)

    return CalculateResponse(
        edges=edges,
        segments=segments,
        summary=summary,
        route_points=route_points,
    )


def _mock_edges(req: CalculateRequest) -> list[Edge]:
    """Gera arestas de exemplo (modo inicial -> onibus -> caminhada final).

    Reproduz a estrutura do payload do SDD: um trecho no modal inicial, uma
    aresta de onibus (com metadados GTFS) e um trecho final a pe.
    """
    o_lat, o_lon = req.origin
    d_lat, d_lon = req.destination
    mode = req.initial_mode
    initial_speed = {
        "walk": 5.0,
        "bike": 20.0,
        "car": 40.0,
        "moto": 45.0,
        "bus": 25.0,
        "uber_car": 35.0,
        "uber_moto": 40.0,
    }.get(mode, 20.0)

    # Ponto intermediario fictio entre origem e destino (embarque no onibus).
    mid_lat = (o_lat + d_lat) / 2
    mid_lon = (o_lon + d_lon) / 2

    edges: list[Edge] = [
        Edge(
            mode=mode,
            means=mode,
            origin=(o_lat, o_lon),
            destination=(mid_lat, mid_lon),
            distance=3.9851,
            time=0.2195,
            cost=0.0,
            effort=6.5758,
            risk=0.0032,
            weight=0.62,
            average_speed_kmh=initial_speed,
            geometry=[[o_lat, o_lon], [mid_lat, mid_lon]],
        ),
        Edge(
            mode="bus",
            means="bus",
            origin=(mid_lat, mid_lon),
            destination=(d_lat, d_lon),
            distance=4.242,
            time=0.1866,
            cost=4.5,
            effort=0.0,
            risk=0.084,
            weight=0.4538,
            average_speed_kmh=25.0,
            line="1 - Rota Teste Recife",
            gtfs_shape_id="shape_1",
            gtfs_validation=True,
            geometry=[
                [mid_lat, mid_lon],
                [(mid_lat + d_lat) / 2, (mid_lon + d_lon) / 2],
                [d_lat, d_lon],
            ],
        ),
        Edge(
            mode="walk",
            means="walk",
            origin=(d_lat, d_lon),
            destination=(d_lat, d_lon),
            distance=0.0268,
            time=0.0059,
            cost=0.0,
            effort=0.1475,
            risk=0.0008,
            weight=0.0112,
            average_speed_kmh=5.0,
            geometry=[[d_lat, d_lon], [d_lat, d_lon]],
        ),
    ]
    return edges


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
        # Velocidade media ponderada por distancia (km / h).
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
        # Propaga metadados GTFS quando o trecho e de onibus.
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
