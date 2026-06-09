"""Algoritmo de Dijkstra para a camada de transporte publico / GTFS.

Usado nas arestas de onibus. Diferente da malha viaria continua, a rede de
onibus nao tem uma heuristica espacial confiavel (uma linha pode dar voltas
ate chegar ao destino), por isso a busca uniforme de Dijkstra e mais adequada
que o A*: ela expande sempre o no de menor custo acumulado, sem estimar o que
falta.

O custo de cada aresta vem de `weight_fn` (montada pelo `routing_service` com os
pesos do banco). Dijkstra equivale a um A* com heuristica nula; mantemos a
implementacao separada para deixar explicito o algoritmo cobrado na disciplina.
"""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Callable
from typing import Any

No = tuple[float, float]
Aresta = dict[str, Any]

WeightFn = Callable[[Aresta], float]
EdgeFilter = Callable[[Aresta], bool]


def dijkstra(
    graph: Any,
    origem: No,
    destino: No,
    weight_fn: WeightFn,
    *,
    edge_filter: EdgeFilter | None = None,
) -> list[Aresta]:
    """Encontra o caminho de menor custo na rede GTFS via Dijkstra.

    Args:
        graph: estrutura com `neighbors(no) -> list[Aresta]` (arestas modal="bus"
            mais baldeacoes a pe).
        origem: parada/no de partida.
        destino: parada/no de chegada.
        weight_fn: custo (>= 0) de transitar por uma aresta, ja com os pesos do
            banco aplicados.
        edge_filter: se fornecido, descarta arestas para as quais retorna False
            (ex.: manter apenas arestas de onibus).

    Returns:
        Lista ordenada de arestas (dicts) compondo a rota de onibus, incluindo os
        metadados GTFS (line, shape_id). Vazia se nao houver caminho.
    """
    if origem == destino:
        return []

    counter = itertools.count()
    open_heap: list[tuple[float, int, No]] = [(0.0, next(counter), origem)]
    dist: dict[No, float] = {origem: 0.0}
    came_from: dict[No, Aresta] = {}
    visited: set[No] = set()

    while open_heap:
        custo_atual, _, atual = heapq.heappop(open_heap)
        if atual == destino:
            return _reconstruct(came_from, destino)
        if atual in visited:
            continue
        visited.add(atual)

        for aresta in graph.neighbors(atual):
            if edge_filter is not None and not edge_filter(aresta):
                continue
            vizinho = aresta["to"]
            if vizinho in visited:
                continue
            novo_custo = custo_atual + weight_fn(aresta)
            if novo_custo < dist.get(vizinho, float("inf")):
                dist[vizinho] = novo_custo
                came_from[vizinho] = aresta
                heapq.heappush(open_heap, (novo_custo, next(counter), vizinho))

    return []


def _reconstruct(came_from: dict[No, Aresta], destino: No) -> list[Aresta]:
    """Refaz o caminho da origem ao destino a partir das arestas registradas."""
    caminho: list[Aresta] = []
    no = destino
    while no in came_from:
        aresta = came_from[no]
        caminho.append(aresta)
        no = aresta["from"]
    caminho.reverse()
    return caminho
