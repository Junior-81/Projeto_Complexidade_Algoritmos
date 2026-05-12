import osmnx as ox
import networkx as nx
import pandas as pd
from typing import Dict, Tuple, List, Optional
from math import radians, cos, sin, asin, sqrt
import re
import pickle
import hashlib
from pathlib import Path


class GraphBuilder:
    """Constrói grafo multimodal para roteamento."""

    CACHE_DIR = Path(__file__).parent.parent / "output" / ".graph_cache"
    CACHE_META_FILE = CACHE_DIR / "graph_meta.txt"
    CACHE_GRAPH_FILE = CACHE_DIR / "multimodal_graph.pkl"

    def __init__(self, location: str = "Recife, Brazil"):
        self.location = location
        self.base_graph = None
        self.multimodal_graph = None
        self.merged_graph = None
        self.speed_data = {}
        self.flood_data = {}

    @staticmethod
    def _get_data_hash() -> str:
        """Gera hash dos arquivos de dados (CSVs, GTFS) para validar cache."""
        hash_obj = hashlib.md5()
        data_dir = Path(__file__).parent.parent / "data"
        
        if not data_dir.exists():
            return "no_data_dir"
        
        # Hash CSVs + GTFS
        for pattern in ["*.csv", "bus_gtfs/*"]:
            for file in sorted(data_dir.glob(pattern)):
                if file.is_file():
                    try:
                        with open(file, "rb") as f:
                            hash_obj.update(f.read()[:10000])  # Primeiros 10KB
                    except:
                        pass
        return hash_obj.hexdigest()[:16]

    @staticmethod
    def save_graph_cache(graph: nx.MultiDiGraph, speed_data: Dict):
        """Salva grafo processado em cache com hash de validação."""
        GraphBuilder.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            data_hash = GraphBuilder._get_data_hash()
            with open(GraphBuilder.CACHE_GRAPH_FILE, "wb") as f:
                pickle.dump({"graph": graph, "speed_data": speed_data}, f)
            with open(GraphBuilder.CACHE_META_FILE, "w") as f:
                f.write(data_hash)
            print(f"✓ Grafo cacheado (hash={data_hash})")
            return True
        except Exception as e:
            print(f"⚠ Falha ao cachear grafo: {e}")
            return False

    @staticmethod
    def load_graph_cache() -> Optional[Tuple[nx.MultiDiGraph, Dict]]:
        """Carrega grafo de cache se válido."""
        if not GraphBuilder.CACHE_GRAPH_FILE.exists() or not GraphBuilder.CACHE_META_FILE.exists():
            return None
        
        try:
            with open(GraphBuilder.CACHE_META_FILE, "r") as f:
                cached_hash = f.read().strip()
            current_hash = GraphBuilder._get_data_hash()
            
            if cached_hash != current_hash:
                print(f"⚠ Cache inválido (hash: {cached_hash} → {current_hash}, dados mudaram)")
                return None
            
            with open(GraphBuilder.CACHE_GRAPH_FILE, "rb") as f:
                data = pickle.load(f)
            print(f"✓ Grafo carregado de cache (hash={cached_hash})")
            return data["graph"], data["speed_data"]
        except Exception as e:
            print(f"⚠ Falha ao carregar cache: {e}")
            return None

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

                # Caminhada deve ser navegável em ambos os sentidos.
                if modal == "walk" and u != v:
                    self.multimodal_graph.add_edge(
                        v,
                        u,
                        modal=modal,
                        distance_km=distance,
                        length=data.get("length", 0),
                        osm_speed_kmh=osm_speed_kmh,
                        original_key=key,
                    )

        print(f"✓ Grafo multimodal criado: {len(self.multimodal_graph.edges)} arestas")
        return self.multimodal_graph

    def _nearest_node_with_fallback(self, lon: float, lat: float) -> int:
        """Retorna o nó mais próximo usando OSMnx; fallback manual se faltar sklearn."""
        try:
            return ox.distance.nearest_nodes(self.base_graph, lon, lat)
        except Exception:
            nearest = None
            min_dist = float("inf")
            for node, data in self.base_graph.nodes(data=True):
                node_lon = float(data.get("x", 0.0) or 0.0)
                node_lat = float(data.get("y", 0.0) or 0.0)
                d = (node_lon - lon) ** 2 + (node_lat - lat) ** 2
                if d < min_dist:
                    min_dist = d
                    nearest = node
            if nearest is None:
                raise ValueError("Nao foi possivel localizar no mais proximo no grafo")
            return nearest

    def _connect_stops_with_walk(
        self, stops_df: pd.DataFrame, max_walk_to_stop_km: float = 0.5
    ) -> int:
        """Conecta nós de rua com nós de parada via arestas walk dentro de um raio."""
        base_nodes = []
        for node, data in self.base_graph.nodes(data=True):
            lon = data.get("x")
            lat = data.get("y")
            if lon is None or lat is None:
                continue
            base_nodes.append((node, float(lat), float(lon)))

        added = 0
        for _, stop in stops_df.iterrows():
            stop_id = str(stop.get("stop_id", "")).strip()
            stop_lat = float(stop.get("stop_lat", 0.0) or 0.0)
            stop_lon = float(stop.get("stop_lon", 0.0) or 0.0)
            if not stop_id:
                continue

            for node, node_lat, node_lon in base_nodes:
                dist_km = self.haversine(node_lon, node_lat, stop_lon, stop_lat)
                if dist_km > max_walk_to_stop_km:
                    continue

                self.multimodal_graph.add_edge(
                    node,
                    stop_id,
                    modal="walk",
                    distance_km=dist_km,
                    source="gtfs_stop_access",
                )
                self.multimodal_graph.add_edge(
                    stop_id,
                    node,
                    modal="walk",
                    distance_km=dist_km,
                    source="gtfs_stop_access",
                )
                added += 2

        return added

    def _add_bus_edges_from_stop_times(
        self,
        stops_df: pd.DataFrame,
        stop_times_df: pd.DataFrame,
        trips_df: pd.DataFrame,
        routes_df: pd.DataFrame,
    ) -> int:
        """Cria arestas bus entre paradas consecutivas na sequencia de cada trip."""
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
        trip_to_line = {}
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

        added_edges = 0
        grouped = stop_times_df.groupby("trip_id")
        for trip_id, group in grouped:
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
                dist_km = self.haversine(from_lon, from_lat, to_lon, to_lat)

                self.multimodal_graph.add_edge(
                    from_stop,
                    to_stop,
                    modal="bus",
                    distance_km=dist_km,
                    line=trip_to_line.get(str(trip_id), "GTFS"),
                    gtfs_trip_id=str(trip_id),
                    source="gtfs_stop_times",
                )
                added_edges += 1

        return added_edges

    def _integrate_gtfs_stop_based(self, gtfs_dir: str) -> bool:
        """Integra GTFS no formato operacional (stops + stop_times)."""
        stops_path = f"{gtfs_dir}/stops.txt"
        stop_times_path = f"{gtfs_dir}/stop_times.txt"
        trips_path = f"{gtfs_dir}/trips.txt"
        routes_path = f"{gtfs_dir}/routes.txt"

        if not (
            pd.io.common.file_exists(stops_path)
            and pd.io.common.file_exists(stop_times_path)
            and pd.io.common.file_exists(trips_path)
            and pd.io.common.file_exists(routes_path)
        ):
            return False

        stops_df = pd.read_csv(stops_path)
        stop_times_df = pd.read_csv(stop_times_path)
        trips_df = pd.read_csv(trips_path)
        routes_df = pd.read_csv(routes_path)

        if stops_df.empty or stop_times_df.empty:
            return False

        print(f"Stops carregados: {len(stops_df)}")
        print(f"Stop times carregados: {len(stop_times_df)}")
        print(f"Trips carregados: {len(trips_df)}")
        print(f"Routes carregadas: {len(routes_df)}")

        added_stops = 0
        for _, stop in stops_df.iterrows():
            stop_id = str(stop.get("stop_id", "")).strip()
            if not stop_id:
                continue
            stop_lat = float(stop.get("stop_lat", 0.0) or 0.0)
            stop_lon = float(stop.get("stop_lon", 0.0) or 0.0)
            stop_name = str(stop.get("stop_name", stop_id)).strip() or stop_id
            self.multimodal_graph.add_node(
                stop_id,
                x=stop_lon,
                y=stop_lat,
                type="stop",
                stop_id=stop_id,
                stop_name=stop_name,
            )
            added_stops += 1

        walk_edges = self._connect_stops_with_walk(stops_df, max_walk_to_stop_km=0.5)
        bus_edges = self._add_bus_edges_from_stop_times(
            stops_df, stop_times_df, trips_df, routes_df
        )

        print(f"✓ Nós de parada adicionados: {added_stops}")
        print(f"✓ Arestas walk↔stop adicionadas: {walk_edges}")
        print(f"✓ Arestas bus (stop_times) adicionadas: {bus_edges}")

        return bus_edges > 0

    def _integrate_gtfs_shape_based(self, gtfs_dir: str) -> int:
        """Fallback legado: integra GTFS por geometria de shapes."""
        shapes_path = f"{gtfs_dir}/shapes.txt"
        trips_path = f"{gtfs_dir}/trips.txt"
        routes_path = f"{gtfs_dir}/routes.txt"

        shapes_df = pd.read_csv(shapes_path)
        trips_df = pd.read_csv(trips_path)
        routes_df = pd.read_csv(routes_path)

        print(f"Shapes carregados: {len(shapes_df)}")
        print(f"Trips carregados: {len(trips_df)}")
        print(f"Routes carregadas: {len(routes_df)}")

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

                node = self._nearest_node_with_fallback(lon, lat)
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
                            source="gtfs_shape",
                        )
                        added_edges += 1

                prev = curr

        return added_edges

    def add_gtfs_bus_routes(self, gtfs_dir: str):
        """Adiciona arestas GTFS priorizando modelo stop-based (stops/stop_times)."""
        if self.base_graph is None or self.multimodal_graph is None:
            print("Grafo base/multimodal não carregado para integrar GTFS")
            return

        try:
            if self._integrate_gtfs_stop_based(gtfs_dir):
                print("✓ Integração GTFS stop-based concluída")
                return

            print("! stops/stop_times indisponiveis; usando fallback shape-based")
            added_edges = self._integrate_gtfs_shape_based(gtfs_dir)
            print(f"✓ Arestas de ônibus GTFS (shape) adicionadas: {added_edges}")

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
