import heapq
import logging
import math
from typing import Optional

import networkx as nx

from app.graph.normalizer import Normalizer

logger = logging.getLogger(__name__)


class AStarMultimodal:
    def __init__(self, graph: nx.MultiDiGraph, normalizer_params: dict):
        self.graph = graph
        self.normalizer_params = normalizer_params
        self.closed_set = set()
        self.open_set = set()
        self.came_from = {}
        self.g_score = {}
        self.f_score = {}

    @staticmethod
    def _resolve_edge_speed(edge_data: dict, modal: str, speed_getter) -> float:
        if modal in {"car", "moto", "uber_car", "uber_moto", "uber"}:
            return float(edge_data.get("osm_speed_kmh", 50.0) or 50.0)
        return speed_getter(modal) if speed_getter is not None else 10

    @staticmethod
    def _is_transition_allowed(
        current_modal: str, next_modal: str, start_modal: str
    ) -> bool:
        if current_modal == next_modal:
            return True

        if start_modal == "walk":
            if current_modal == "walk" and next_modal in {
                "walk", "bus", "uber_car", "uber_moto", "bike",
            }:
                return True
            if current_modal in {"bus", "uber_car", "uber_moto", "bike"}:
                return next_modal == "walk"
            return False

        return True

    def heuristic(self, current, goal, speed_getter) -> float:
        node_curr, _ = current
        node_goal, _ = goal
        try:
            curr_data = self.graph.nodes[node_curr]
            goal_data = self.graph.nodes[node_goal]

            lat1 = curr_data.get("y", 0)
            lon1 = curr_data.get("x", 0)
            lat2 = goal_data.get("y", 0)
            lon2 = goal_data.get("x", 0)

            dlat = lat2 - lat1
            dlon = lon2 - lon1
            distance_km = math.sqrt(dlat**2 + dlon**2) * 111

            max_speed = max(
                speed_getter(m)
                for m in ["walk", "bike", "car", "moto", "bus", "uber_car", "uber_moto"]
            )
            time = distance_km / max_speed if max_speed > 0 else distance_km

            time_norm = Normalizer.normalize_value(
                time, self.normalizer_params["time"]["min"],
                self.normalizer_params["time"]["max"],
            )
            return time_norm * 100 
        except Exception:
            return 0

    def get_edge_cost(
        self, u, v, modal, cost_calc, risk_calc, rain_factor, tide_factor, speed_getter
    ) -> tuple[float, float, float]:
        try:
            edge_data = None
            if self.graph.has_edge(u, v):
                for _, data in self.graph[u][v].items():
                    if data.get("modal") == modal:
                        edge_data = data
                        break

            if edge_data is None:
                return (float("inf"), float("inf"), float("inf"))

            distance_km = edge_data.get("distance_km", 0)
            speed = self._resolve_edge_speed(edge_data, modal, speed_getter)
            tempo_base = distance_km / speed if speed > 0 else 10
            tempo_final = tempo_base * rain_factor * tide_factor
            time_minutes = tempo_final * 60

            custo_rota = cost_calc.calculate_routing_cost(
                modal, distance_km, time_minutes=time_minutes, avg_speed_kmh=speed,
                rain_factor=rain_factor, tide_factor=tide_factor,
            )

            climate_factor = rain_factor * tide_factor
            risco = risk_calc.get_adjusted_risk(modal, climate_factor) * distance_km / 10

            tempo_norm = Normalizer.normalize_value(
                tempo_final, self.normalizer_params["time"]["min"],
                self.normalizer_params["time"]["max"],
            )
            custo_norm = Normalizer.normalize_value(
                custo_rota, self.normalizer_params["cost"]["min"],
                self.normalizer_params["cost"]["max"],
            )
            risco_norm = Normalizer.normalize_value(
                risco, self.normalizer_params["risk"]["min"],
                self.normalizer_params["risk"]["max"],
            )
            return (tempo_norm, custo_norm, risco_norm)
        except Exception:
            return (1.0, 1.0, 1.0)

    def search(
        self,
        start: tuple[int, str],
        goal: tuple[int, str],
        cost_calc,
        risk_calc,
        rain_factor: float = 1.0,
        tide_factor: float = 1.0,
        speed_getter=None,
        start_modal: str | None = None,
        allowed_modes: set[str] | None = None,
        bus_required: bool = False,
        max_walk_distance_km: float | None = None,
        walk_penalty_factor: float = 1.0,
        boarding_penalty: float = 0.0,
    ) -> Optional[list[tuple[int, str]]]:
        """Executa A* para encontrar o caminho otimo."""
        if speed_getter is None:
            speed_getter = lambda m: 10
        if start_modal is None:
            start_modal = start[1]

        allowed_modes_norm = {m.lower() for m in allowed_modes} if allowed_modes else None

        start_used_bus = start[1].lower() == "bus"
        start_state = (start[0], start[1], start_used_bus)

        self.closed_set = set()
        self.open_set = {start_state}
        self.came_from = {}
        self.g_score = {start_state: 0}

        h_start = self.heuristic(start, goal, speed_getter)
        self.f_score = {start_state: h_start}
        pq = [(h_start, start_state)]

        iteration = 0
        max_iterations = 100000

        while self.open_set and iteration < max_iterations:
            iteration += 1
            _, current = heapq.heappop(pq)

            if current not in self.open_set:
                continue

            self.open_set.remove(current)
            self.closed_set.add(current)

            if current[0] == goal[0] and (not bus_required or current[2]):
                return self._reconstruct_path(current)

            node_curr, modal_curr, used_bus_curr = current

            for neighbor in self.graph.neighbors(node_curr):
                for _, edge_data in self.graph[node_curr][neighbor].items():
                    modal_neighbor = edge_data.get("modal", modal_curr)

                    if (
                        allowed_modes_norm is not None
                        and modal_neighbor.lower() not in allowed_modes_norm
                    ):
                        continue

                    if modal_neighbor == "walk" and max_walk_distance_km is not None:
                        if float(edge_data.get("distance_km", 0.0) or 0.0) > float(
                            max_walk_distance_km
                        ):
                            continue

                    if not self._is_transition_allowed(
                        modal_curr, modal_neighbor, start_modal
                    ):
                        continue

                    used_bus_neighbor = used_bus_curr or (modal_neighbor == "bus")
                    state_neighbor = (neighbor, modal_neighbor, used_bus_neighbor)
                    if state_neighbor in self.closed_set:
                        continue

                    tempo_norm, custo_norm, risco_norm = self.get_edge_cost(
                        node_curr, neighbor, modal_neighbor, cost_calc, risk_calc,
                        rain_factor, tide_factor, speed_getter,
                    )

                    weight = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
                    if modal_neighbor == "walk" and walk_penalty_factor != 1.0:
                        weight *= walk_penalty_factor
                    if modal_neighbor == "bus" and modal_curr != "bus":
                        weight += boarding_penalty

                    tentative_g = self.g_score.get(current, float("inf")) + weight

                    if (
                        state_neighbor not in self.g_score
                        or tentative_g < self.g_score[state_neighbor]
                    ):
                        self.came_from[state_neighbor] = current
                        self.g_score[state_neighbor] = tentative_g
                        h = self.heuristic(
                            (neighbor, modal_neighbor), goal, speed_getter
                        )
                        f = tentative_g + h
                        self.f_score[state_neighbor] = f
                        if state_neighbor not in self.open_set:
                            self.open_set.add(state_neighbor)
                            heapq.heappush(pq, (f, state_neighbor))

        logger.warning("A* nao encontrou caminho apos %d iteracoes", iteration)
        return None

    def _reconstruct_path(self, current) -> list[tuple[int, str]]:
        path = [current]
        while current in self.came_from:
            current = self.came_from[current]
            path.append(current)
        path.reverse()
        return [(node, modal) for node, modal, _ in path]
