"""Construção do grafo multimodal a partir do grafo base do OSM."""

from __future__ import annotations

import networkx as nx

from graph.geo import parse_osm_speed_kmh

MODALS_REPLICADOS = ("walk", "bike", "car", "moto", "uber_car", "uber_moto")
WALK_MAX_DISTANCE_KM = 5.0


def build(base_graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Replica cada aresta do grafo base para os modais suportados.

    - `walk` é descartado em arestas com `distance > WALK_MAX_DISTANCE_KM`.
    - `walk` é navegável nos dois sentidos.
    """
    multimodal = nx.MultiDiGraph()

    for node, data in base_graph.nodes(data=True):
        multimodal.add_node(node, **data)

    for u, v, key, data in base_graph.edges(keys=True, data=True):
        distance_km = data.get("length", 0) / 1000
        osm_speed_kmh = parse_osm_speed_kmh(data.get("maxspeed"))

        for modal in MODALS_REPLICADOS:
            if modal == "walk" and distance_km > WALK_MAX_DISTANCE_KM:
                continue

            multimodal.add_edge(
                u,
                v,
                modal=modal,
                distance_km=distance_km,
                length=data.get("length", 0),
                osm_speed_kmh=osm_speed_kmh,
                original_key=key,
            )

            # Caminhada deve ser bidirecional.
            if modal == "walk" and u != v:
                multimodal.add_edge(
                    v,
                    u,
                    modal=modal,
                    distance_km=distance_km,
                    length=data.get("length", 0),
                    osm_speed_kmh=osm_speed_kmh,
                    original_key=key,
                )

    print(f"✓ Grafo multimodal criado: {len(multimodal.edges)} arestas")
    return multimodal
