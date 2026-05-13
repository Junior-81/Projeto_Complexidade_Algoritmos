"""Base compartilhada entre Dijkstra e A* sobre o grafo multimodal.

Estado de busca: `(node_id, modal_atual, used_bus)`.

Subclasses implementam apenas `priority(state, g_score)` — quem decide se
a fronteira usa só `g(n)` (Dijkstra) ou `g(n) + h(n)` (A*).
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

import networkx as nx

from graph.normalizer import Normalizer

State = Tuple[int, str, bool]  # (node, modal, used_bus)

MOTORIZED = {"car", "moto", "uber_car", "uber_moto", "uber"}
TRANSITION_BOARD_FROM_WALK = {"walk", "bus", "uber_car", "uber_moto", "bike"}
TRANSITION_DISMOUNT = {"bus", "uber_car", "uber_moto", "bike"}

WEIGHT_TIME = 0.5
WEIGHT_COST = 0.3
WEIGHT_RISK = 0.2

MAX_ITERATIONS = 100_000


class MultimodalSearchBase:
    """Lógica comum: transições, custo de aresta, expansão e reconstrução."""

    name = "search"

    def __init__(self, graph: nx.MultiDiGraph, normalizer_params: Dict):
        self.graph = graph
        self.normalizer_params = normalizer_params
        self.closed_set: set = set()
        self.open_set: set = set()
        self.came_from: Dict[State, State] = {}
        self.g_score: Dict[State, float] = {}

    # ------------------------------------------------------------------
    # Hook que subclasses sobrescrevem
    # ------------------------------------------------------------------

    def priority(self, state: State, g_score: float, goal: Tuple[int, str], speed_getter) -> float:
        """Prioridade do estado na fila. Dijkstra: g(n). A*: g(n) + h(n)."""
        return g_score

    # ------------------------------------------------------------------
    # Regras de transição e custo (compartilhadas)
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_edge_speed(edge_data: Dict, modal: str, speed_getter) -> float:
        """Velocidade da aresta: OSM para motorizados; speed_getter para o resto."""
        if modal in MOTORIZED:
            return float(edge_data.get("osm_speed_kmh", 50.0) or 50.0)
        return speed_getter(modal) if speed_getter is not None else 10

    @staticmethod
    def _is_transition_allowed(current_modal: str, next_modal: str, start_modal: str) -> bool:
        """Quando inicia a pé, evita embarcar em carro/moto próprios."""
        if current_modal == next_modal:
            return True

        if start_modal == "walk":
            if current_modal == "walk" and next_modal in TRANSITION_BOARD_FROM_WALK:
                return True
            if current_modal in TRANSITION_DISMOUNT:
                return next_modal == "walk"
            return False

        return True

    def compute_edge_cost(
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
        """Retorna (tempo_norm, custo_norm, risco_norm) ou (inf, inf, inf) se aresta inválida."""
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

            custo_rota = cost_calc.calculate_routing_cost(
                modal,
                distance_km,
                time_minutes=tempo_final * 60,
                avg_speed_kmh=speed,
                rain_factor=rain_factor,
                tide_factor=tide_factor,
            )

            climate_factor = rain_factor * tide_factor
            risco = risk_calc.get_adjusted_risk(modal, climate_factor) * distance_km / 10

            params = self.normalizer_params
            return (
                Normalizer.normalize_value(tempo_final, params["time"]["min"], params["time"]["max"]),
                Normalizer.normalize_value(custo_rota, params["cost"]["min"], params["cost"]["max"]),
                Normalizer.normalize_value(risco, params["risk"]["min"], params["risk"]["max"]),
            )
        except Exception:
            return (1.0, 1.0, 1.0)

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

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
        allowed_modes: set[str] | None = None,
        bus_required: bool = False,
        max_walk_distance_km: float | None = None,
        walk_penalty_factor: float = 1.0,
    ) -> Optional[List[Tuple[int, str]]]:
        if speed_getter is None:
            speed_getter = lambda _m: 10

        if start_modal is None:
            start_modal = start[1]

        allowed_modes_norm = (
            {m.lower() for m in allowed_modes} if allowed_modes else None
        )

        start_used_bus = start[1].lower() == "bus"
        start_state: State = (start[0], start[1], start_used_bus)

        self.closed_set = set()
        self.open_set = {start_state}
        self.came_from = {}
        self.g_score = {start_state: 0.0}

        initial_priority = self.priority(start_state, 0.0, goal, speed_getter)
        pq: list[tuple[float, State]] = [(initial_priority, start_state)]

        iteration = 0
        while self.open_set and iteration < MAX_ITERATIONS:
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

                    if allowed_modes_norm is not None and modal_neighbor.lower() not in allowed_modes_norm:
                        continue

                    if modal_neighbor == "walk" and max_walk_distance_km is not None:
                        if float(edge_data.get("distance_km", 0.0) or 0.0) > float(max_walk_distance_km):
                            continue

                    if not self._is_transition_allowed(modal_curr, modal_neighbor, start_modal):
                        continue

                    used_bus_neighbor = used_bus_curr or (modal_neighbor == "bus")
                    state_neighbor: State = (neighbor, modal_neighbor, used_bus_neighbor)

                    if state_neighbor in self.closed_set:
                        continue

                    tempo_norm, custo_norm, risco_norm = self.compute_edge_cost(
                        node_curr,
                        neighbor,
                        modal_neighbor,
                        cost_calc,
                        risk_calc,
                        rain_factor,
                        tide_factor,
                        speed_getter,
                    )

                    weight = (
                        WEIGHT_TIME * tempo_norm
                        + WEIGHT_COST * custo_norm
                        + WEIGHT_RISK * risco_norm
                    )
                    if modal_neighbor == "walk" and walk_penalty_factor != 1.0:
                        weight *= walk_penalty_factor

                    tentative_g = self.g_score[current] + weight

                    if state_neighbor not in self.g_score or tentative_g < self.g_score[state_neighbor]:
                        self.came_from[state_neighbor] = current
                        self.g_score[state_neighbor] = tentative_g

                        f = self.priority(
                            state_neighbor, tentative_g, goal, speed_getter
                        )

                        if state_neighbor not in self.open_set:
                            self.open_set.add(state_neighbor)
                        heapq.heappush(pq, (f, state_neighbor))

        print(f"{self.name} nao encontrou caminho apos {iteration} iteracoes")
        return None

    def _reconstruct_path(self, current: State) -> List[Tuple[int, str]]:
        path = [current]
        while current in self.came_from:
            current = self.came_from[current]
            path.append(current)
        path.reverse()
        return [(node, modal) for node, modal, _ in path]
