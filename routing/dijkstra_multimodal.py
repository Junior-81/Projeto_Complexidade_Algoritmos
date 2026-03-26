import heapq
from typing import Dict, Tuple, List, Optional
import networkx as nx

from graph.normalizer import Normalizer


class DijkstraMultimodal:
    """
    Implementa Dijkstra para roteamento multimodal.

    Estado: (node, modal_atual)
    """

    def __init__(self, graph: nx.MultiDiGraph, normalizer_params: Dict):
        self.graph = graph
        self.normalizer_params = normalizer_params
        self.closed_set = set()
        self.open_set = set()
        self.came_from = {}
        self.g_score = {}

    @staticmethod
    def _resolve_edge_speed(edge_data: Dict, modal: str, speed_getter) -> float:
        """Usa velocidade da aresta do OSMnx quando existir; fallback 50 km/h."""
        if modal in {"car", "moto", "uber_car", "uber_moto", "uber"}:
            return float(edge_data.get("osm_speed_kmh", 50.0) or 50.0)
        return speed_getter(modal) if speed_getter is not None else 10

    @staticmethod
    def _is_transition_allowed(
        current_modal: str, next_modal: str, start_modal: str
    ) -> bool:
        """Controla trocas de modal para evitar veiculo proprio quando inicia a pe."""
        if current_modal == next_modal:
            return True

        if start_modal == "walk":
            return current_modal == "walk" and next_modal in {
                "walk",
                "bus",
                "uber_car",
                "uber_moto",
                "bike",
            }

        return True

    def get_edge_cost(
        self,
        u: int,
        v: int,
        modal: str,
        cost_calc,
        risk_calc,
        rain_factor: float,
        tide_factor: float,
        speed_getter,
    ) -> Tuple[float, float, float]:
        """
        Calcula tempo, custo e risco normalizados de uma aresta.

        Returns:
            (tempo_normalizado, custo_normalizado, risco_normalizado)
        """

        try:
            edge_data = None
            if self.graph.has_edge(u, v):
                for _, data in self.graph[u][v].items():
                    if data.get("modal") == modal:
                        edge_data = data
                        break

            if edge_data is None:
                return (float("inf"), float("inf"), float("inf"))

            distance_km = float(edge_data.get("distance_km", 0))
            speed = self._resolve_edge_speed(edge_data, modal, speed_getter)

            tempo_base = distance_km / speed if speed > 0 else 10
            tempo_final = tempo_base * rain_factor * tide_factor
            time_minutes = tempo_final * 60

            custo = cost_calc.calculate_cost(
                modal,
                distance_km,
                time_minutes=time_minutes,
                avg_speed_kmh=speed,
                rain_factor=rain_factor,
            )

            climate_factor = rain_factor * tide_factor
            risco_base = risk_calc.get_adjusted_risk(modal, climate_factor)
            risco = risco_base * distance_km / 10

            tempo_norm = Normalizer.normalize_value(
                tempo_final,
                self.normalizer_params["time"]["min"],
                self.normalizer_params["time"]["max"],
            )
            custo_norm = Normalizer.normalize_value(
                custo,
                self.normalizer_params["cost"]["min"],
                self.normalizer_params["cost"]["max"],
            )
            risco_norm = Normalizer.normalize_value(
                risco,
                self.normalizer_params["risk"]["min"],
                self.normalizer_params["risk"]["max"],
            )

            return (tempo_norm, custo_norm, risco_norm)

        except Exception:
            return (1.0, 1.0, 1.0)

    def search(
        self,
        start: Tuple[int, str],
        goal: Tuple[int, str],
        cost_calc,
        risk_calc,
        rain_factor: float = 1.0,
        tide_factor: float = 1.0,
        speed_getter=None,
        start_modal: str | None = None,
    ) -> Optional[List[Tuple[int, str]]]:
        """Executa Dijkstra para encontrar o caminho otimo."""

        if speed_getter is None:
            speed_getter = lambda m: 10

        if start_modal is None:
            start_modal = start[1]

        self.closed_set = set()
        self.open_set = {start}
        self.came_from = {}
        self.g_score = {start: 0.0}

        pq = [(0.0, start)]
        iteration = 0
        max_iterations = 100000

        while self.open_set and iteration < max_iterations:
            iteration += 1
            current_cost, current = heapq.heappop(pq)

            if current not in self.open_set:
                continue

            self.open_set.remove(current)
            self.closed_set.add(current)

            if current[0] == goal[0]:
                return self._reconstruct_path(current)

            node_curr, modal_curr = current

            for neighbor in self.graph.neighbors(node_curr):
                for _, edge_data in self.graph[node_curr][neighbor].items():
                    modal_neighbor = edge_data.get("modal", modal_curr)

                    if not self._is_transition_allowed(
                        modal_curr, modal_neighbor, start_modal
                    ):
                        continue

                    state_neighbor = (neighbor, modal_neighbor)
                    if state_neighbor in self.closed_set:
                        continue

                    tempo_norm, custo_norm, risco_norm = self.get_edge_cost(
                        node_curr,
                        neighbor,
                        modal_neighbor,
                        cost_calc,
                        risk_calc,
                        rain_factor,
                        tide_factor,
                        speed_getter,
                    )

                    weight = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
                    tentative_g = current_cost + weight

                    if (
                        state_neighbor not in self.g_score
                        or tentative_g < self.g_score[state_neighbor]
                    ):
                        self.came_from[state_neighbor] = current
                        self.g_score[state_neighbor] = tentative_g

                        if state_neighbor not in self.open_set:
                            self.open_set.add(state_neighbor)
                        heapq.heappush(pq, (tentative_g, state_neighbor))

        print(f"Dijkstra nao encontrou caminho apos {iteration} iteracoes")
        return None

    def _reconstruct_path(self, current: Tuple[int, str]) -> List[Tuple[int, str]]:
        """Reconstrói o caminho a partir do mapa de precedentes."""
        path = [current]
        while current in self.came_from:
            current = self.came_from[current]
            path.append(current)
        path.reverse()
        return path
