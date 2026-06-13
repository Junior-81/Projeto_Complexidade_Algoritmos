import logging
import pickle
import re
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent / "output" / ".graph_cache"
_BASE_GRAPH_FILE = _CACHE_DIR / "base_graph_osmnx.pkl"
# _busv2: arestas de onibus + acesso a pe multi-no (K vizinhos no raio). Nome
# novo invalida caches antigos sem precisar limpar o volume manualmente.
_MULTIMODAL_FILE = _CACHE_DIR / "multimodal_graph_busv2.pkl"

_STREET_MODALS = ["walk", "bike", "car", "moto", "uber_car", "uber_moto"]

# Acesso a pe parada<->rua: ate K nos de rua mais proximos dentro do raio.
_ACCESS_K = 6
_ACCESS_RADIUS_KM = 0.4

_DEFAULT_SPEEDS = {
    "walk": 5,
    "bike": 20,
    "car": 40,
    "moto": 50,
    "bus": 25,
    "uber_car": 40,
    "uber_moto": 45,
    "uber": 40,
}


class GraphBuilder:
    def __init__(self, location: str = "Recife, Brazil"):
        self.location = location
        self.base_graph: nx.MultiDiGraph | None = None
        self.multimodal_graph: nx.MultiDiGraph | None = None
        self.speed_data: dict[str, float] = {}

    @staticmethod
    def _load_pickle(path: Path):
        if not path.exists():
            return None
        try:
            with open(path, "rb") as fp:
                return pickle.load(fp)
        except Exception as exc:
            logger.warning("Falha ao carregar cache %s: %s", path.name, exc)
            return None

    @staticmethod
    def _save_pickle(path: Path, obj) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as fp:
                pickle.dump(obj, fp)
        except Exception as exc:  
            logger.warning("Falha ao cachear %s: %s", path.name, exc)

    def load_base_graph(self) -> nx.MultiDiGraph:
        cached = self._load_pickle(_BASE_GRAPH_FILE)
        if cached is not None:
            self.base_graph = cached
            logger.info(
                "Base graph do cache: %d nos, %d arestas",
                len(self.base_graph.nodes),
                len(self.base_graph.edges),
            )
            return self.base_graph

        logger.info("Baixando malha de '%s' via OSMnx (pode levar minutos)...", self.location)
        self.base_graph = ox.graph_from_place(
            self.location, network_type="drive", simplify=True
        )
        logger.info(
            "Base graph carregado: %d nos, %d arestas",
            len(self.base_graph.nodes),
            len(self.base_graph.edges),
        )
        self._save_pickle(_BASE_GRAPH_FILE, self.base_graph)
        return self.base_graph

    @staticmethod
    def _parse_osm_speed_kmh(raw_speed) -> float:
        if raw_speed is None:
            return 50.0
        if isinstance(raw_speed, list) and raw_speed:
            raw_speed = raw_speed[0]
        text = str(raw_speed).lower()
        match = re.search(r"\d+(?:\.\d+)?", text)
        if not match:
            return 50.0
        value = float(match.group())
        if "mph" in text:
            value *= 1.60934
        return value if value > 0 else 50.0

    def build_multimodal_graph(self, bus_network: dict | None = None) -> nx.MultiDiGraph:
        """Constroi (ou carrega do cache) o grafo multimodal: ruas + onibus.

        `bus_network` (opcional): {"stops": {stop_id: (lat, lon)}, "segments":
        [(from_stop, to_stop, line), ...]}. Quando fornecido, adiciona as arestas
        `bus` entre paradas consecutivas e o acesso a pe parada<->rua.
        """
        cached = self._load_pickle(_MULTIMODAL_FILE)

        if cached is not None:
            self.multimodal_graph = cached
            logger.info(
                "Grafo multimodal do cache: %d arestas",
                len(self.multimodal_graph.edges),
            )
            return self.multimodal_graph

        if self.base_graph is None:
            self.load_base_graph()

        graph = nx.MultiDiGraph()
        for node, data in self.base_graph.nodes(data=True):
            graph.add_node(node, **data)

        for u, v, key, data in self.base_graph.edges(keys=True, data=True):
            distance = data.get("length", 0) / 1000
            osm_speed_kmh = self._parse_osm_speed_kmh(data.get("maxspeed"))

            for modal in _STREET_MODALS:
                if modal == "walk" and distance > 5:
                    continue
                graph.add_edge(
                    u, v, modal=modal, distance_km=distance,
                    length=data.get("length", 0), osm_speed_kmh=osm_speed_kmh,
                    original_key=key,
                )
                if modal == "walk" and u != v:
                    graph.add_edge(
                        v, u, modal=modal, distance_km=distance,
                        length=data.get("length", 0), osm_speed_kmh=osm_speed_kmh,
                        original_key=key,
                    )

        logger.info("Arestas de rua criadas: %d", len(graph.edges))

        if bus_network:
            self._add_bus_network(graph, bus_network)

        self.multimodal_graph = graph
        logger.info("Grafo multimodal final: %d arestas", len(graph.edges))
        self._save_pickle(_MULTIMODAL_FILE, graph)
        return graph

    def _add_bus_network(self, graph: nx.MultiDiGraph, bus_network: dict) -> None:
        """Adiciona arestas `bus` (paradas consecutivas) + acesso a pe parada<->rua."""
        stop_coords: dict[str, tuple[float, float]] = bus_network.get("stops", {})
        segments = bus_network.get("segments", [])

        used: set[str] = set()
        for from_stop, to_stop, _ in segments:
            used.add(from_stop)
            used.add(to_stop)

        # 1) Nos de parada (somente os referenciados por algum segmento).
        for stop_id in used:
            coord = stop_coords.get(stop_id)
            if coord is None:
                continue
            lat, lon = coord
            graph.add_node(stop_id, x=lon, y=lat, type="stop", stop_id=stop_id)

        # 2) Arestas de onibus entre paradas consecutivas (ja deduplicadas).
        bus_edges = 0
        for from_stop, to_stop, line in segments:
            f, t = stop_coords.get(from_stop), stop_coords.get(to_stop)
            if f is None or t is None:
                continue
            dist = self.haversine(f[1], f[0], t[1], t[0])
            graph.add_edge(
                from_stop, to_stop, modal="bus", distance_km=dist,
                line=line or "GTFS", source="gtfs",
            )
            bus_edges += 1

        # 3) Acesso a pe: liga cada parada ao no de rua mais proximo (vetorizado
        #    com numpy, pois scipy/sklearn nao estao instalados).
        base_ids, xs, ys = [], [], []
        for node, data in self.base_graph.nodes(data=True):
            x, y = data.get("x"), data.get("y")
            if x is None or y is None:
                continue
            base_ids.append(node)
            xs.append(float(x))
            ys.append(float(y))
        base_ids_arr = np.array(base_ids, dtype=object)
        xs_arr = np.array(xs)
        ys_arr = np.array(ys)

        # Conecta cada parada aos K nos de rua mais proximos dentro do raio. Com
        # varios pontos de acesso, o pedestre embarca/desembarca sem precisar
        # passar pelo unico no mais proximo (o que antes o forcava a andar tudo).
        k_candidates = min(_ACCESS_K, len(base_ids_arr))
        access_edges = 0
        for stop_id in used:
            coord = stop_coords.get(stop_id)
            if coord is None:
                continue
            lat, lon = coord
            d2 = (xs_arr - lon) ** 2 + (ys_arr - lat) ** 2
            cand = np.argpartition(d2, k_candidates - 1)[:k_candidates]
            cand = cand[np.argsort(d2[cand])]  # ordena os candidatos por distancia
            connected = 0
            for idx in cand:
                idx = int(idx)
                dist = self.haversine(lon, lat, float(xs_arr[idx]), float(ys_arr[idx]))
                if dist > _ACCESS_RADIUS_KM:
                    if connected == 0:
                        # garante ao menos 1 acesso mesmo se a parada e remota
                        node = base_ids_arr[idx]
                        graph.add_edge(stop_id, node, modal="walk", distance_km=dist, source="access")
                        graph.add_edge(node, stop_id, modal="walk", distance_km=dist, source="access")
                        access_edges += 2
                    break
                node = base_ids_arr[idx]
                graph.add_edge(stop_id, node, modal="walk", distance_km=dist, source="access")
                graph.add_edge(node, stop_id, modal="walk", distance_km=dist, source="access")
                access_edges += 2
                connected += 1

        logger.info(
            "Rede de onibus: %d paradas, %d arestas bus, %d arestas de acesso a pe",
            len(used), bus_edges, access_edges,
        )

    def load_speed_data(self, speed_df: pd.DataFrame) -> None:
        if speed_df is not None and not speed_df.empty:
            mode_col = "mode" if "mode" in speed_df.columns else "modal"
            for _, row in speed_df.iterrows():
                modal = str(row[mode_col]).lower()
                self.speed_data[modal] = float(row.get("speed_kmh", 10))
        for modal, speed in _DEFAULT_SPEEDS.items():
            self.speed_data.setdefault(modal, speed)

    def get_speed(self, modal: str) -> float:
        modal_norm = modal.lower()
        if modal_norm == "uber":
            modal_norm = "uber_car"
        return self.speed_data.get(modal_norm, 10)

    def nearest_node(self, lat: float, lon: float):
        try:
            return ox.distance.nearest_nodes(self.base_graph, lon, lat)
        except Exception: 
            nearest, min_dist = None, float("inf")
            for node, data in self.base_graph.nodes(data=True):
                node_lon = float(data.get("x", 0.0) or 0.0)
                node_lat = float(data.get("y", 0.0) or 0.0)
                d = (node_lon - lon) ** 2 + (node_lat - lat) ** 2
                if d < min_dist:
                    min_dist, nearest = d, node
            if nearest is None:
                raise ValueError("Nao foi possivel localizar no mais proximo no grafo")
            return nearest

    @staticmethod
    def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 2 * asin(sqrt(a)) * 6371
