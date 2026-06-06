"""Construcao do grafo multimodal (STUB).

Esta camada montara o grafo combinando:
  * a malha viaria continua (ruas) -> arestas walk / bike / car / moto;
  * o feed GTFS do Grande Recife -> arestas `bus` entre paradas consecutivas,
    mais arestas `walk` ligando cada parada as ruas num raio de ~0,5 km.

Os metodos abaixo sao esqueletos: definem a interface esperada pelos algoritmos
de roteamento. A logica matematica sera implementada posteriormente.
"""

from typing import Any

# Tipo de no do grafo: tupla (latitude, longitude).
No = tuple[float, float]


class GraphBuilder:
    """Constroi e mantem o grafo multimodal em memoria."""

    def __init__(self) -> None:
        # Lista de adjacencia: no -> lista de arestas (dicts com modo/peso/etc).
        self.adjacencia: dict[No, list[dict[str, Any]]] = {}

    def build_street_graph(self, modais: list[str]) -> None:
        """Constroi as arestas da malha viaria continua para os modais dados.

        TODO: carregar a malha (ex.: OpenStreetMap / OSMnx) e gerar uma aresta
        por segmento de rua, com distancia e geometria reais.
        """
        raise NotImplementedError("Construcao da malha viaria ainda nao implementada.")

    def add_gtfs_bus_routes(self, gtfs_dir: str) -> None:
        """Adiciona as arestas de onibus a partir do feed GTFS.

        TODO: ler stops/trips/stop_times, criar arestas modal="bus" entre paradas
        consecutivas de cada viagem e conectar paradas as ruas (raio 0,5 km).
        """
        raise NotImplementedError("Integracao GTFS ainda nao implementada.")

    def neighbors(self, no: No) -> list[dict[str, Any]]:
        """Retorna as arestas que saem de `no` (usado por A* / Dijkstra)."""
        return self.adjacencia.get(no, [])
