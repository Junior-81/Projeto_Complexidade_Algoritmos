"""Algoritmo de Dijkstra para o transporte publico / GTFS (STUB).

Usado nas arestas de onibus. Diferente da malha viaria continua, o grafo GTFS
depende de paradas e horarios predefinidos, sem uma heuristica espacial confiavel
(uma linha pode dar voltas), por isso a busca uniforme de Dijkstra e mais
adequada que o A*.

A complexidade matematica sera implementada posteriormente; aqui fica apenas a
assinatura e o contrato esperado.
"""

from typing import Any

No = tuple[float, float]


def dijkstra(
    graph: Any,
    origem: No,
    destino: No,
) -> list[dict[str, Any]]:
    """Encontra o caminho de menor peso na rede GTFS via Dijkstra.

    Args:
        graph: estrutura com `neighbors(no)` (arestas modal="bus" + baldeacoes).
        origem: parada/no de partida.
        destino: parada/no de chegada.

    Returns:
        Lista ordenada de arestas (dicts) compondo a rota de onibus, incluindo
        metadados GTFS (linha, gtfs_shape_id). Vazia se nao houver caminho.

    TODO: implementar a fila de prioridade considerando horarios das viagens e os
    pesos dinamicos de `weights_service`.
    """
    raise NotImplementedError("Dijkstra ainda nao implementado.")
