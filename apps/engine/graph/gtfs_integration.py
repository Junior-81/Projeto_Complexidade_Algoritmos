"""Integração GTFS: adiciona paradas e arestas de ônibus ao grafo multimodal.

Prioriza o modelo *stop-based* (stops + stop_times + trips + routes).
Faz fallback para *shape-based* (shapes + trips + routes) quando o primeiro falha.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd

from graph.geo import haversine
from graph.osm_loader import nearest_node_with_fallback

MAX_WALK_TO_STOP_KM = 0.5


# ---------------------------------------------------------------------------
# Stop-based (preferido)
# ---------------------------------------------------------------------------

def _connect_stops_with_walk(
    base_graph: nx.MultiDiGraph,
    multimodal: nx.MultiDiGraph,
    stops_df: pd.DataFrame,
    max_walk_km: float = MAX_WALK_TO_STOP_KM,
) -> int:
    """Liga nós de rua a paradas próximas via aresta `walk` bidirecional."""
    base_nodes = []
    for node, data in base_graph.nodes(data=True):
        lon = data.get("x")
        lat = data.get("y")
        if lon is None or lat is None:
            continue
        base_nodes.append((node, float(lat), float(lon)))

    added = 0
    for _, stop in stops_df.iterrows():
        stop_id = str(stop.get("stop_id", "")).strip()
        if not stop_id:
            continue
        stop_lat = float(stop.get("stop_lat", 0.0) or 0.0)
        stop_lon = float(stop.get("stop_lon", 0.0) or 0.0)

        for node, node_lat, node_lon in base_nodes:
            dist_km = haversine(node_lon, node_lat, stop_lon, stop_lat)
            if dist_km > max_walk_km:
                continue

            multimodal.add_edge(
                node, stop_id, modal="walk", distance_km=dist_km, source="gtfs_stop_access"
            )
            multimodal.add_edge(
                stop_id, node, modal="walk", distance_km=dist_km, source="gtfs_stop_access"
            )
            added += 2

    return added


def _add_bus_edges_from_stop_times(
    multimodal: nx.MultiDiGraph,
    stops_df: pd.DataFrame,
    stop_times_df: pd.DataFrame,
    trips_df: pd.DataFrame,
    routes_df: pd.DataFrame,
) -> int:
    """Cria arestas `bus` entre paradas consecutivas de cada viagem do GTFS."""
    stop_coords = {}
    for _, row in stops_df.iterrows():
        stop_id = str(row.get("stop_id", "")).strip()
        if not stop_id:
            continue
        stop_coords[stop_id] = (
            float(row.get("stop_lat", 0.0) or 0.0),
            float(row.get("stop_lon", 0.0) or 0.0),
        )

    route_meta = routes_df.set_index("route_id") if not routes_df.empty else None
    trip_to_line: dict[str, str] = {}
    for _, trip in trips_df.iterrows():
        trip_id = str(trip.get("trip_id", "")).strip()
        route_id = str(trip.get("route_id", "")).strip()
        line = route_id or "GTFS"
        if route_meta is not None and route_id in route_meta.index:
            route_row = route_meta.loc[route_id]
            short_name = str(route_row.get("route_short_name", route_id))
            long_name = str(route_row.get("route_long_name", "")).strip()
            line = f"{short_name} - {long_name}" if long_name else short_name
        if trip_id:
            trip_to_line[trip_id] = line

    added = 0
    for trip_id, group in stop_times_df.groupby("trip_id"):
        ordered = group.sort_values("stop_sequence")
        for i in range(len(ordered) - 1):
            from_stop = str(ordered.iloc[i].get("stop_id", "")).strip()
            to_stop = str(ordered.iloc[i + 1].get("stop_id", "")).strip()
            if not from_stop or not to_stop or from_stop == to_stop:
                continue
            if from_stop not in stop_coords or to_stop not in stop_coords:
                continue

            from_lat, from_lon = stop_coords[from_stop]
            to_lat, to_lon = stop_coords[to_stop]
            dist_km = haversine(from_lon, from_lat, to_lon, to_lat)

            multimodal.add_edge(
                from_stop,
                to_stop,
                modal="bus",
                distance_km=dist_km,
                line=trip_to_line.get(str(trip_id), "GTFS"),
                gtfs_trip_id=str(trip_id),
                source="gtfs_stop_times",
            )
            added += 1

    return added


def _integrate_stop_based(
    base_graph: nx.MultiDiGraph, multimodal: nx.MultiDiGraph, gtfs_dir: str
) -> bool:
    """Integra GTFS via stops/stop_times. Retorna True se adicionou ao menos uma aresta."""
    paths = {
        name: f"{gtfs_dir}/{name}.txt"
        for name in ("stops", "stop_times", "trips", "routes")
    }
    if not all(pd.io.common.file_exists(p) for p in paths.values()):
        return False

    stops_df = pd.read_csv(paths["stops"])
    stop_times_df = pd.read_csv(paths["stop_times"])
    trips_df = pd.read_csv(paths["trips"])
    routes_df = pd.read_csv(paths["routes"])

    if stops_df.empty or stop_times_df.empty:
        return False

    print(f"Stops: {len(stops_df)} | Stop times: {len(stop_times_df)} | Trips: {len(trips_df)} | Routes: {len(routes_df)}")

    added_stops = 0
    for _, stop in stops_df.iterrows():
        stop_id = str(stop.get("stop_id", "")).strip()
        if not stop_id:
            continue
        multimodal.add_node(
            stop_id,
            x=float(stop.get("stop_lon", 0.0) or 0.0),
            y=float(stop.get("stop_lat", 0.0) or 0.0),
            type="stop",
            stop_id=stop_id,
            stop_name=str(stop.get("stop_name", stop_id)).strip() or stop_id,
        )
        added_stops += 1

    walk_edges = _connect_stops_with_walk(base_graph, multimodal, stops_df)
    bus_edges = _add_bus_edges_from_stop_times(
        multimodal, stops_df, stop_times_df, trips_df, routes_df
    )

    print(f"✓ Stops: {added_stops} | walk↔stop: {walk_edges} | bus: {bus_edges}")
    return bus_edges > 0


# ---------------------------------------------------------------------------
# Shape-based (fallback)
# ---------------------------------------------------------------------------

def _integrate_shape_based(
    base_graph: nx.MultiDiGraph, multimodal: nx.MultiDiGraph, gtfs_dir: str
) -> int:
    """Fallback: integra GTFS pela geometria de `shapes.txt`."""
    shapes_df = pd.read_csv(f"{gtfs_dir}/shapes.txt")
    trips_df = pd.read_csv(f"{gtfs_dir}/trips.txt")
    routes_df = pd.read_csv(f"{gtfs_dir}/routes.txt")

    print(f"Shapes: {len(shapes_df)} | Trips: {len(trips_df)} | Routes: {len(routes_df)}")

    route_meta = routes_df.set_index("route_id")
    shape_to_route: dict[str, str] = {}
    for _, trip in trips_df.drop_duplicates(subset=["shape_id"]).iterrows():
        shape_id = str(trip.get("shape_id", ""))
        route_id = str(trip.get("route_id", ""))
        if shape_id and route_id in route_meta.index:
            route_row = route_meta.loc[route_id]
            short_name = str(route_row.get("route_short_name", route_id))
            long_name = str(route_row.get("route_long_name", "")).strip()
            shape_to_route[shape_id] = (
                f"{short_name} - {long_name}" if long_name else short_name
            )

    added = 0
    grouped = shapes_df.sort_values(["shape_id", "shape_pt_sequence"]).groupby("shape_id")
    for shape_id, group in grouped:
        prev = None
        for _, row in group.iterrows():
            lat = float(row.get("shape_pt_lat", 0))
            lon = float(row.get("shape_pt_lon", 0))
            dist_m = float(row.get("shape_dist_traveled", 0) or 0)
            node = nearest_node_with_fallback(base_graph, lon, lat)
            curr = (node, lat, lon, dist_m)

            if prev is not None:
                prev_node, prev_lat, prev_lon, prev_dist_m = prev
                curr_node, curr_lat, curr_lon, curr_dist_m = curr

                if curr_node != prev_node:
                    seg_dist_km = max((curr_dist_m - prev_dist_m) / 1000.0, 0)
                    if seg_dist_km <= 0:
                        seg_dist_km = haversine(prev_lon, prev_lat, curr_lon, curr_lat)

                    multimodal.add_edge(
                        prev_node,
                        curr_node,
                        modal="bus",
                        distance_km=seg_dist_km,
                        gtfs_shape_id=str(shape_id),
                        line=shape_to_route.get(str(shape_id), "GTFS"),
                        source="gtfs_shape",
                    )
                    added += 1
            prev = curr

    return added


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def integrate(
    base_graph: nx.MultiDiGraph, multimodal: nx.MultiDiGraph, gtfs_dir: str
) -> None:
    """Tenta integração stop-based; cai para shape-based se necessário."""
    if base_graph is None or multimodal is None:
        print("Grafo base/multimodal não carregado para integrar GTFS")
        return

    try:
        if _integrate_stop_based(base_graph, multimodal, gtfs_dir):
            print("✓ Integração GTFS stop-based concluída")
            return

        print("! stops/stop_times indisponiveis; usando fallback shape-based")
        added = _integrate_shape_based(base_graph, multimodal, gtfs_dir)
        print(f"✓ Arestas de ônibus GTFS (shape) adicionadas: {added}")
    except Exception as exc:
        print(f"✗ Erro ao integrar GTFS: {exc}")
