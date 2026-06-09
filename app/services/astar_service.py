"""Algoritmo A* (A-Estrela) para a malha de proximidade dos modais continuos.

Usado nos modais de malha continua (walk, bike, car, moto, uber_*). A busca e
guiada por uma heuristica espacial (distancia de Haversine ate o destino), que
torna a exploracao mais eficiente que o Dijkstra em grafos com geometria.

O custo real de cada aresta vem de `weight_fn` (montada pelo `routing_service`
a partir dos pesos do banco: velocidade do modal, risco, alagamento). A
heuristica devolve um limite inferior admissivel desse custo, garantindo que o
A* encontre o caminho otimo.
"""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Callable
from typing import Any

from app.graph.geo import haversine_km

No = tuple[float, float]

# Aresta do grafo: dict com no de origem/destino, distancia, geometria e metadados.
Aresta = dict[str, Any]

# Tipos das funcoes injetadas pelo servico de roteamento.
WeightFn = Callable[[Aresta], float]
Heuristica = Callable[[No, No], float]
EdgeFilter = Callable[[Aresta], bool]


def heuristica_haversine(origem: No, destino: No) -> float:
    """Estimativa de custo restante entre dois nos: distancia de Haversine (km).

    E a menor distancia possivel sobre a esfera, logo nunca superestima o
    trajeto real -> heuristica admissivel (condicao para o A* ser otimo).
    """
    return haversine_km(origem, destino)


def astar(
    graph: Any,
    origem: No,
    destino: No,
    weight_fn: WeightFn,
    heuristica: Heuristica = heuristica_haversine,
    *,
    edge_filter: EdgeFilter | None = None,
) -> list[Aresta]:
    """Encontra o caminho de menor custo na malha continua via A*.

    Args:
        graph: estrutura com `neighbors(no) -> list[Aresta]` (ver GraphBuilder).
        origem: no de partida.
        destino: no de chegada.
        weight_fn: custo (>= 0) de transitar por uma aresta, ja com os pesos do
            banco aplicados.
        heuristica: estimativa admissivel do custo restante, na mesma unidade de
            `weight_fn`.
        edge_filter: se fornecido, descarta arestas para as quais retorna False
            (ex.: manter apenas arestas de rua, ignorando as de onibus).

    Returns:
        Lista ordenada de arestas (dicts) compondo a rota. Vazia se nao houver
        caminho.
    """
    if origem == destino:
        return []

    # Contador desempata entradas com mesmo f-score, evitando comparar dicts.
    counter = itertools.count()
    # Fila de prioridade por f-score = g-score + heuristica.
    open_heap: list[tuple[float, int, No]] = [(0.0, next(counter), origem)]
    # Menor custo conhecido da origem ate cada no (g-score).
    g_score: dict[No, float] = {origem: 0.0}
    # Aresta usada para chegar a cada no (reconstrucao do caminho).
    came_from: dict[No, Aresta] = {}
    visited: set[No] = set()

    while open_heap:
        _, _, atual = heapq.heappop(open_heap)
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
            tentativo = g_score[atual] + weight_fn(aresta)
            if tentativo < g_score.get(vizinho, float("inf")):
                g_score[vizinho] = tentativo
                came_from[vizinho] = aresta
                f = tentativo + heuristica(vizinho, destino)
                heapq.heappush(open_heap, (f, next(counter), vizinho))

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
