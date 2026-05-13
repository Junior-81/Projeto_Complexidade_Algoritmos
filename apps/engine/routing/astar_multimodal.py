"""A* multimodal: prioridade da fila é f(n) = g(n) + h(n).

A heurística estima o tempo até o destino em linha reta dividido pela maior
velocidade disponível, depois normalizado para a mesma escala do peso.
"""

from __future__ import annotations

import math
from typing import Tuple

from graph.normalizer import Normalizer
from routing.search_base import MultimodalSearchBase, State

ALL_MODALS_FOR_HEURISTIC = ("walk", "bike", "car", "moto", "bus", "uber_car", "uber_moto")


class AStarMultimodal(MultimodalSearchBase):
    """A* — usa heurística admissível para reduzir estados expandidos."""

    name = "A*"

    def heuristic(
        self, current: Tuple[int, str], goal: Tuple[int, str], speed_getter
    ) -> float:
        """Tempo estimado até o destino (em escala normalizada)."""
        try:
            curr_data = self.graph.nodes[current[0]]
            goal_data = self.graph.nodes[goal[0]]

            lat1 = curr_data.get("y", 0)
            lon1 = curr_data.get("x", 0)
            lat2 = goal_data.get("y", 0)
            lon2 = goal_data.get("x", 0)

            # Distância euclidiana aproximada em graus * 111 km/grau.
            distance_km = math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111

            max_speed = max(speed_getter(m) for m in ALL_MODALS_FOR_HEURISTIC)
            tempo = distance_km / max_speed if max_speed > 0 else distance_km

            time_norm = Normalizer.normalize_value(
                tempo,
                self.normalizer_params["time"]["min"],
                self.normalizer_params["time"]["max"],
            )
            # Multiplica por 100 para manter a mesma escala usada antes da refatoração.
            return time_norm * 100
        except Exception:
            return 0

    def priority(
        self, state: State, g_score: float, goal: Tuple[int, str], speed_getter
    ) -> float:
        h = self.heuristic((state[0], state[1]), goal, speed_getter)
        return g_score + h
