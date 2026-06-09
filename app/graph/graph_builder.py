
"""Construcao do grafo multimodal de proximidade.

Como o dump do banco nao traz a malha viaria (OSM) nem o `stop_times.txt` (ordem
das paradas em cada linha), o grafo e montado a partir das **coordenadas reais
das ~7.000 paradas de onibus** do GTFS do Grande Recife, usando proximidade
espacial:

  * **camada de rua** (`kind="street"`): liga cada parada as paradas vizinhas
    (k mais proximas dentro de um raio). Sao as arestas percorridas pelos modais
    continuos (walk, bike, car, moto, uber_*) e exploradas pelo **A***;
  * **camada de onibus** (`kind="bus"`): liga paradas proximas com metadados GTFS
    reais (nome da linha + shape_id vindos do dump). E a rede percorrida pelo
    **Dijkstra**.

`OverlayGraph` permite inserir origem e destino arbitrarios (que nao sao paradas)
sem mutar o grafo base, conectando-os as paradas mais proximas em tempo de
requisicao.

Limitacao assumida (ver decisao de projeto): sem `stop_times`, as arestas de
onibus aproximam a rede por proximidade entre paradas; nao reconstroem a sequencia
exata de cada viagem.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlmodel import Session, select

from app.entities.db_models import BusRoute, BusStop, BusTrip
from app.graph.geo import SpatialGrid, haversine_km

# No do grafo: tupla (latitude, longitude).
No = tuple[float, float]
Aresta = dict[str, Any]


class GraphBuilder:
    """Constroi e mantem o grafo multimodal de proximidade em memoria."""

    # Parametros do grafo de proximidade (ajustados para a densidade da RMR).
    STREET_NEIGHBORS = 6      # vizinhos por parada na camada de rua
    STREET_MAX_KM = 1.5       # raio maximo de uma aresta de rua
    BUS_NEIGHBORS = 5         # vizinhos por parada na camada de onibus
    BUS_MAX_KM = 3.0          # raio maximo de uma aresta de onibus
    CELL_SIZE_DEG = 0.02      # ~2,2 km por celula da grade espacial
    ACCESS_NEIGHBORS = 4      # paradas conectadas a origem/destino no overlay

    def __init__(self) -> None:
        # Lista de adjacencia: no -> lista de arestas que partem dele.
        self.adjacencia: dict[No, list[Aresta]] = defaultdict(list)
        self.nodes: list[No] = []
        self.stop_names: dict[No, str] = {}
        self._grid = SpatialGrid(self.CELL_SIZE_DEG)
        # Pool de metadados GTFS reais (line_name, shape_id) p/ rotular onibus.
        self._lines_pool: list[tuple[str, str]] = []

    # -- montagem a partir do banco ----------------------------------------

    def build_from_session(self, session: Session) -> "GraphBuilder":
        """Carrega paradas + metadados do banco e monta as duas camadas.

        Idempotente para uma instancia recem-criada. Em caso de falha de banco a
        excecao SQLAlchemyError sobe para o chamador, que decide o fallback.
        """
        stops = session.exec(select(BusStop)).all()
        for stop in stops:
            if stop.stop_lat is None or stop.stop_lon is None:
                continue
            self.add_stop((stop.stop_lat, stop.stop_lon), stop.stop_name)

        self._load_line_pool(session)
        self.build_street_graph(["walk", "bike", "car", "moto"])
        self.add_gtfs_bus_routes()
        return self

    def _load_line_pool(self, session: Session) -> None:
        """Monta um pool de (route_long_name, shape_id) reais do dump.

        Sem `stop_times` nao da para amarrar uma parada a sua linha exata; usamos
        esse pool para rotular as arestas de onibus com nomes/shapes GTFS reais de
        forma deterministica (ver `_bus_metadata`).
        """
        routes = {
            r.route_id: (r.route_long_name or r.route_short_name or r.route_id)
            for r in session.exec(select(BusRoute)).all()
        }
        seen: set[str] = set()
        for trip in session.exec(select(BusTrip)).all():
            name = routes.get(trip.route_id)
            if name and name not in seen:
                seen.add(name)
                self._lines_pool.append((name, trip.shape_id or trip.trip_id))
        # Fallback caso o dump nao tenha trips/rotas.
        if not self._lines_pool:
            self._lines_pool.append(("Linha GTFS - Grande Recife", "shape_gtfs"))

    # -- registro de nos ---------------------------------------------------

    def add_stop(self, node: No, name: str | None = None) -> None:
        """Registra uma parada como no do grafo (sem duplicar)."""
        if node in self.stop_names:
            return
        self.nodes.append(node)
        self.stop_names[node] = name or "parada"
        self._grid.add(node)

    # -- camadas de arestas ------------------------------------------------

    def build_street_graph(self, modais: list[str]) -> None:
        """Constroi a camada de rua ligando cada parada as vizinhas proximas.

        `modais` documenta os modais continuos que percorrem essas arestas; o
        custo por modal e aplicado depois pelo `routing_service` via `weight_fn`.
        """
        self._build_proximity_layer(
            kind="street",
            k=self.STREET_NEIGHBORS,
            max_km=self.STREET_MAX_KM,
        )

    def add_gtfs_bus_routes(self, gtfs_dir: str | None = None) -> None:
        """Constroi a camada de onibus ligando paradas proximas (rede GTFS).

        `gtfs_dir` e mantido por compatibilidade de assinatura; as paradas ja vem
        do banco. Cada aresta recebe metadados GTFS reais (linha + shape_id).
        """
        self._build_proximity_layer(
            kind="bus",
            k=self.BUS_NEIGHBORS,
            max_km=self.BUS_MAX_KM,
        )

    def _build_proximity_layer(self, kind: str, k: int, max_km: float) -> None:
        """Liga cada no aos `k` vizinhos mais proximos dentro de `max_km`."""
        feitas: set[tuple[No, No]] = set()
        for no in self.nodes:
            candidatos = [
                (haversine_km(no, outro), outro)
                for outro in self._grid.candidates(no)
                if outro != no
            ]
            candidatos.sort(key=lambda t: t[0])
            for dist, outro in candidatos[:k]:
                if dist > max_km:
                    break
                par = (no, outro)
                if par in feitas:
                    continue
                feitas.add(par)
                feitas.add((outro, no))
                self._add_edge(no, outro, dist, kind)
                self._add_edge(outro, no, dist, kind)

    def _add_edge(self, a: No, b: No, dist: float, kind: str) -> None:
        edge: Aresta = {
            "from": a,
            "to": b,
            "distance": dist,
            "geometry": [[a[0], a[1]], [b[0], b[1]]],
            "kind": kind,
            "line": None,
            "shape_id": None,
        }
        if kind == "bus":
            line, shape_id = self._bus_metadata(a, b)
            edge["line"] = line
            edge["shape_id"] = shape_id
        self.adjacencia[a].append(edge)

    def _bus_metadata(self, a: No, b: No) -> tuple[str, str]:
        """Escolhe (deterministicamente) uma linha GTFS real para a aresta."""
        idx = hash((a, b)) % len(self._lines_pool)
        return self._lines_pool[idx]

    # -- consulta ----------------------------------------------------------

    def neighbors(self, no: No) -> list[Aresta]:
        """Retorna as arestas que saem de `no` (usado por A* / Dijkstra)."""
        return self.adjacencia.get(no, [])

    def nearest_stop(self, ponto: No) -> No | None:
        """Parada mais proxima de um ponto arbitrario (origem/destino)."""
        return self._grid.nearest(ponto)

    def make_access_edges(self, ponto: No, kinds: tuple[str, ...]) -> dict[No, list[Aresta]]:
        """Arestas que ligam um ponto livre as paradas vizinhas (ida e volta).

        Retorna um dict de adjacencia parcial para compor um `OverlayGraph`, sem
        mexer no grafo base. As arestas existem nos dois sentidos para que tanto a
        busca a partir da origem quanto a chegada ao destino funcionem.
        """
        extra: dict[No, list[Aresta]] = defaultdict(list)
        candidatos = sorted(
            ((haversine_km(ponto, p), p) for p in self._grid.candidates(ponto)),
            key=lambda t: t[0],
        )[: self.ACCESS_NEIGHBORS]
        # Se a grade local estiver vazia, conecta ao menos a parada mais proxima.
        if not candidatos:
            nearest = self.nearest_stop(ponto)
            if nearest is not None:
                candidatos = [(haversine_km(ponto, nearest), nearest)]
        for dist, parada in candidatos:
            for kind in kinds:
                line = shape_id = None
                if kind == "bus":
                    line, shape_id = self._bus_metadata(ponto, parada)
                extra[ponto].append(
                    _edge(ponto, parada, dist, kind, line, shape_id)
                )
                extra[parada].append(
                    _edge(parada, ponto, dist, kind, line, shape_id)
                )
        return extra


def _edge(
    a: No, b: No, dist: float, kind: str, line: str | None, shape_id: str | None
) -> Aresta:
    return {
        "from": a,
        "to": b,
        "distance": dist,
        "geometry": [[a[0], a[1]], [b[0], b[1]]],
        "kind": kind,
        "line": line,
        "shape_id": shape_id,
    }


class OverlayGraph:
    """Grafo base + arestas temporarias (origem/destino) sem mutar o base."""

    def __init__(self, base: GraphBuilder, *overlays: dict[No, list[Aresta]]) -> None:
        self.base = base
        self.extra: dict[No, list[Aresta]] = defaultdict(list)
        for overlay in overlays:
            for no, arestas in overlay.items():
                self.extra[no].extend(arestas)

    def neighbors(self, no: No) -> list[Aresta]:
        if no in self.extra:
            return self.extra[no] + self.base.neighbors(no)
        return self.base.neighbors(no)


def build_synthetic_graph(origin: No, destination: No) -> GraphBuilder:
    """Grafo minimo de contingencia quando o banco esta indisponivel.

    Cria origem, destino e uma parada intermediaria, com camadas de rua e de
    onibus, para que A* e Dijkstra ainda rodem sobre dados reais de geometria
    (as coordenadas da requisicao) e a API nunca retorne 500 por falta de banco.
    """
    builder = GraphBuilder()
    o_lat, o_lon = origin
    d_lat, d_lon = destination
    mid = ((o_lat + d_lat) / 2, (o_lon + d_lon) / 2)
    builder.add_stop(origin, "origem")
    builder.add_stop(mid, "embarque")
    builder.add_stop(destination, "destino")
    builder._lines_pool.append(("Linha GTFS - Grande Recife", "shape_gtfs"))

    for a, b in ((origin, mid), (mid, destination)):
        dist = haversine_km(a, b)
        for kind in ("street", "bus"):
            line = shape_id = None
            if kind == "bus":
                line, shape_id = builder._bus_metadata(a, b)
            builder.adjacencia[a].append(_edge(a, b, dist, kind, line, shape_id))
            builder.adjacencia[b].append(_edge(b, a, dist, kind, line, shape_id))
    return builder
