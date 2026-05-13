"""Carga do grafo viário base via OSMnx."""

from __future__ import annotations

from typing import Optional

import networkx as nx
import osmnx as ox


def load_base_graph(location: str) -> Optional[nx.MultiDiGraph]:
    """Baixa/carrega o grafo de ruas de `location` (rede `drive`, simplificado)."""
    print(f"Carregando grafo de {location}...")
    try:
        graph = ox.graph_from_place(location, network_type="drive", simplify=True)
        print(f"✓ Grafo carregado: {len(graph.nodes)} nós, {len(graph.edges)} arestas")
        return graph
    except Exception as exc:
        print(f"✗ Erro ao carregar grafo: {exc}")
        return None


def nearest_node_with_fallback(graph: nx.MultiDiGraph, lon: float, lat: float) -> int:
    """Nó mais próximo via OSMnx; fallback manual se faltar sklearn."""
    try:
        return ox.distance.nearest_nodes(graph, lon, lat)
    except Exception:
        nearest = None
        min_dist = float("inf")
        for node, data in graph.nodes(data=True):
            node_lon = float(data.get("x", 0.0) or 0.0)
            node_lat = float(data.get("y", 0.0) or 0.0)
            d = (node_lon - lon) ** 2 + (node_lat - lat) ** 2
            if d < min_dist:
                min_dist = d
                nearest = node
        if nearest is None:
            raise ValueError("Nao foi possivel localizar no mais proximo no grafo")
        return nearest
