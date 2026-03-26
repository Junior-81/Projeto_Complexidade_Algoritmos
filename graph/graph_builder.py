import osmnx as ox
import networkx as nx
import pandas as pd
from typing import Dict, Tuple, List, Optional
from math import radians, cos, sin, asin, sqrt
import re


class GraphBuilder:
    """Constrói grafo multimodal para roteamento."""

    def __init__(self, location: str = "Recife, Brazil"):
        self.location = location
        self.base_graph = None
        self.multimodal_graph = None
        self.merged_graph = None
        self.speed_data = {}
        self.flood_data = {}

    def load_base_graph(self):
        """Carrega grafo de ruas usando OSMnx."""
        print(f"Carregando grafo de {self.location}...")
        try:
            self.base_graph = ox.graph_from_place(
                self.location, network_type="drive", simplify=True
            )
            print(
                f"✓ Grafo carregado: {len(self.base_graph.nodes)} nós, {len(self.base_graph.edges)} arestas"
            )
            return self.base_graph
        except Exception as e:
            print(f"✗ Erro ao carregar grafo: {e}")
            return None

    def load_speed_data(self, speed_df: pd.DataFrame):
        """Carrega dados de velocidade por modal."""
        if speed_df is not None and not speed_df.empty:
            mode_col = "mode" if "mode" in speed_df.columns else "modal"
            for _, row in speed_df.iterrows():
                modal = str(row[mode_col]).lower()
                speed = float(row.get("speed_kmh", 10))
                self.speed_data[modal] = speed

        # Velocidades padrão
        defaults = {
            "walk": 5,
            "bike": 20,
            "car": 40,
            "moto": 50,
            "bus": 25,
            "uber_car": 40,
            "uber_moto": 45,
            "uber": 40,
        }

        for modal, speed in defaults.items():
            if modal not in self.speed_data:
                self.speed_data[modal] = speed

    @staticmethod
    def _parse_osm_speed_kmh(raw_speed) -> float:
        """Extrai velocidade (km/h) de atributos OSM com fallback seguro."""
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

    def load_flood_data(self, flood_df: pd.DataFrame):
        """Carrega dados de ruas que alagam."""
        if flood_df is not None and not flood_df.empty:
            for _, row in flood_df.iterrows():
                street = row.get("street_name", "").lower()
                multiplier = float(
                    row.get("rain_multiplier", row.get("multiplier", 1.5))
                )
                self.flood_data[street] = multiplier

    def build_multimodal_graph(self) -> nx.MultiDiGraph:
        """Constrói grafo multimodal do grafo base."""

        if self.base_graph is None:
            print("Erro: Grafo base não foi carregado")
            return None

        self.multimodal_graph = nx.MultiDiGraph()

        # Copia nós
        for node, data in self.base_graph.nodes(data=True):
            self.multimodal_graph.add_node(node, **data)

        # Adiciona arestas com identificador de modal
        for u, v, key, data in self.base_graph.edges(keys=True, data=True):
            distance = data.get("length", 0) / 1000  # Converte para km
            osm_speed_kmh = self._parse_osm_speed_kmh(data.get("maxspeed"))

            # Cada aresta do grafo original é replicada para cada modal
            modals = ["walk", "bike", "car", "moto", "uber_car", "uber_moto"]

            for modal in modals:
                # Skip walk em rotas muito longas
                if modal == "walk" and distance > 5:
                    continue

                self.multimodal_graph.add_edge(
                    u,
                    v,
                    modal=modal,
                    distance_km=distance,
                    length=data.get("length", 0),
                    osm_speed_kmh=osm_speed_kmh,
                    original_key=key,
                )

        print(f"✓ Grafo multimodal criado: {len(self.multimodal_graph.edges)} arestas")
        return self.multimodal_graph

    def add_gtfs_bus_routes(self, gtfs_dir: str):
        """Adiciona arestas de ônibus reais usando GTFS (shapes/trips/routes)."""
        if self.base_graph is None or self.multimodal_graph is None:
            print("Grafo base/multimodal não carregado para integrar GTFS")
            return

        try:
            shapes_path = f"{gtfs_dir}/shapes.txt"
            trips_path = f"{gtfs_dir}/trips.txt"
            routes_path = f"{gtfs_dir}/routes.txt"

            shapes_df = pd.read_csv(shapes_path)
            trips_df = pd.read_csv(trips_path)
            routes_df = pd.read_csv(routes_path)

            route_meta = routes_df.set_index("route_id")
            shape_to_route = {}

            for _, trip in trips_df.drop_duplicates(subset=["shape_id"]).iterrows():
                shape_id = str(trip.get("shape_id", ""))
                route_id = str(trip.get("route_id", ""))
                if shape_id and route_id in route_meta.index:
                    route_row = route_meta.loc[route_id]
                    short_name = str(route_row.get("route_short_name", route_id))
                    long_name = str(route_row.get("route_long_name", "")).strip()
                    label = f"{short_name} - {long_name}" if long_name else short_name
                    shape_to_route[shape_id] = label

            added_edges = 0
            grouped = shapes_df.sort_values(["shape_id", "shape_pt_sequence"]).groupby(
                "shape_id"
            )

            for shape_id, group in grouped:
                prev = None
                for _, row in group.iterrows():
                    lat = float(row.get("shape_pt_lat", 0))
                    lon = float(row.get("shape_pt_lon", 0))
                    dist_m = float(row.get("shape_dist_traveled", 0) or 0)

                    node = ox.distance.nearest_nodes(self.base_graph, lon, lat)
                    curr = (node, lat, lon, dist_m)

                    if prev is not None:
                        prev_node, prev_lat, prev_lon, prev_dist_m = prev
                        curr_node, curr_lat, curr_lon, curr_dist_m = curr

                        if curr_node != prev_node:
                            seg_dist_km = max((curr_dist_m - prev_dist_m) / 1000.0, 0)
                            if seg_dist_km <= 0:
                                seg_dist_km = self.haversine(
                                    prev_lon, prev_lat, curr_lon, curr_lat
                                )

                            self.multimodal_graph.add_edge(
                                prev_node,
                                curr_node,
                                modal="bus",
                                distance_km=seg_dist_km,
                                gtfs_shape_id=str(shape_id),
                                line=shape_to_route.get(str(shape_id), "GTFS"),
                                source="gtfs",
                            )
                            added_edges += 1

                    prev = curr

            print(f"✓ Arestas de ônibus GTFS adicionadas: {added_edges}")

        except Exception as e:
            print(f"✗ Erro ao integrar GTFS: {e}")

    def add_bus_routes(self, bus_df: Optional[pd.DataFrame] = None):
        """Adiciona rotas de ônibus ao grafo (se dados disponíveis)."""

        if bus_df is None or bus_df.empty:
            print("Sem dados de rotas de ônibus")
            return

        try:
            for _, row in bus_df.iterrows():
                line = row.get("line", "bus")
                distance = float(row.get("distance", 1))

                # Adiciona nó de parada
                stop_id = f"bus_stop_{line}_{row.name}"
                self.multimodal_graph.add_node(stop_id, modal="bus", line=line)
        except Exception as e:
            print(f"Erro ao adicionar rotas de ônibus: {e}")

    def get_speed(self, modal: str) -> float:
        """Retorna velocidade para um modal."""
        modal_norm = modal.lower()
        if modal_norm == "uber":
            modal_norm = "uber_car"
        return self.speed_data.get(modal_norm, 10)

    def get_flood_multiplier(self, street_name: str) -> float:
        """Retorna multiplicador de alagamento para uma rua."""
        return self.flood_data.get(street_name.lower(), 1.0)

    @staticmethod
    def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Calcula distância em linha reta entre dois pontos (em km).

        Args:
            lon1, lat1: Coordenadas do ponto 1
            lon2, lat2: Coordenadas do ponto 2

        Returns:
            Distância em km
        """
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371  # Raio da Terra em km

        return c * r
