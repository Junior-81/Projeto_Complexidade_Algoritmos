"""GraphBuilder: orquestrador do grafo multimodal.

A construção propriamente dita está em módulos focados:
- `graph.osm_loader`       — grafo viário base (OSMnx)
- `graph.multimodal_builder` — replicação de arestas por modal
- `graph.gtfs_integration`   — paradas e linhas de ônibus
- `graph.graph_cache`        — persistência em disco
- `graph.geo`                — haversine, parse de velocidade
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import networkx as nx
import pandas as pd

from graph import graph_cache
from graph.geo import haversine  # noqa: F401  -- re-exposto p/ compatibilidade
from graph.gtfs_integration import integrate as integrate_gtfs
from graph.multimodal_builder import build as build_multimodal
from graph.osm_loader import load_base_graph

DEFAULT_SPEEDS_KMH = {
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
    """Orquestra carga, construção e enriquecimento do grafo multimodal."""

    def __init__(self, location: str = "Recife, Brazil"):
        self.location = location
        self.base_graph: Optional[nx.MultiDiGraph] = None
        self.multimodal_graph: Optional[nx.MultiDiGraph] = None
        self.speed_data: Dict[str, float] = {}
        self.flood_data: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Cache (delegado a `graph.graph_cache`)
    # ------------------------------------------------------------------

    @staticmethod
    def save_graph_cache(graph: nx.MultiDiGraph, speed_data: Dict) -> bool:
        return graph_cache.save(graph, speed_data)

    @staticmethod
    def load_graph_cache() -> Optional[Tuple[nx.MultiDiGraph, Dict]]:
        return graph_cache.load()

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------

    def load_base_graph(self) -> Optional[nx.MultiDiGraph]:
        self.base_graph = load_base_graph(self.location)
        return self.base_graph

    def load_speed_data(self, speed_df: Optional[pd.DataFrame]) -> None:
        """Carrega velocidades por modal do CSV e completa com defaults."""
        if speed_df is not None and not speed_df.empty:
            mode_col = "mode" if "mode" in speed_df.columns else "modal"
            for _, row in speed_df.iterrows():
                modal = str(row[mode_col]).lower()
                self.speed_data[modal] = float(row.get("speed_kmh", 10))

        for modal, speed in DEFAULT_SPEEDS_KMH.items():
            self.speed_data.setdefault(modal, speed)

    def load_flood_data(self, flood_df: Optional[pd.DataFrame]) -> None:
        """Carrega multiplicadores de alagamento por rua."""
        if flood_df is None or flood_df.empty:
            return
        for _, row in flood_df.iterrows():
            street = str(row.get("street_name", "")).lower()
            multiplier = float(row.get("rain_multiplier", row.get("multiplier", 1.5)))
            self.flood_data[street] = multiplier

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------

    def build_multimodal_graph(self) -> Optional[nx.MultiDiGraph]:
        if self.base_graph is None:
            print("Erro: grafo base não foi carregado")
            return None
        self.multimodal_graph = build_multimodal(self.base_graph)
        return self.multimodal_graph

    def add_gtfs_bus_routes(self, gtfs_dir: str) -> None:
        integrate_gtfs(self.base_graph, self.multimodal_graph, gtfs_dir)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_speed(self, modal: str) -> float:
        modal_norm = modal.lower()
        if modal_norm == "uber":
            modal_norm = "uber_car"
        return self.speed_data.get(modal_norm, 10)

    def get_flood_multiplier(self, street_name: str) -> float:
        return self.flood_data.get(street_name.lower(), 1.0)
