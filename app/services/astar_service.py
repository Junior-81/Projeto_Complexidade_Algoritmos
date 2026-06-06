"""Algoritmo A* (A-Estrela) para malha de ruas continuas (STUB).

Usado nos modais de malha continua (walk, bike, car, moto). A busca e guiada por
uma heuristica espacial (ex.: distancia de Haversine ate o destino), que torna a
exploracao mais eficiente que o Dijkstra em grafos com geometria.

A complexidade matematica sera implementada posteriormente; aqui fica apenas a
assinatura e o contrato esperado.
"""

from collections.abc import Callable
from typing import Any

No = tuple[float, float]


def heuristica_haversine(origem: No, destino: No) -> float:
    """Estimativa de custo restante entre dois nos (distancia em km).

    TODO: implementar a formula de Haversine. Por enquanto e um esqueleto.
    """
    raise NotImplementedError("Heuristica espacial ainda nao implementada.")


def astar(
    graph: Any,
    origem: No,
    destino: No,
    heuristica: Callable[[No, No], float] = heuristica_haversine,
) -> list[dict[str, Any]]:
    """Encontra o caminho de menor peso na malha continua via A*.

    Args:
        graph: estrutura com `neighbors(no)` (ver GraphBuilder).
        origem: no de partida.
        destino: no de chegada.
        heuristica: estimativa admissivel do custo restante.

    Returns:
        Lista ordenada de arestas (dicts) compondo a rota. Vazia se nao houver
        caminho.

    TODO: implementar a fila de prioridade, g-score/f-score e reconstrucao do
    caminho usando os pesos dinamicos de `weights_service`.
    """
    raise NotImplementedError("A* ainda nao implementado.")
