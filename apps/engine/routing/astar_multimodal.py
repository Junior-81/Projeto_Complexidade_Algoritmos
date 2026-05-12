import heapq
import math
from typing import Dict, Tuple, List, Optional, Set
import networkx as nx


class Normalizer:
    """Utilitário para normalização."""

    @staticmethod
    def normalize_value(value: float, min_val: float, max_val: float) -> float:
        """Normaliza um valor usando Min-Max."""
        range_val = max_val - min_val

        if range_val == 0:
            return 0.5

        normalized = (value - min_val) / range_val
        return max(0, min(1, normalized))


class AStarMultimodal:
    """
    Implementa A* para roteamento multimodal.

    Estado: (node, modal_atual)
    Permite troca modal apenas para walk (origem de ônibus/uber).
    """

    def __init__(self, graph: nx.MultiDiGraph, normalizer_params: Dict):
        self.graph = graph
        self.normalizer_params = normalizer_params
        self.closed_set = set()
        self.open_set = set()
        self.came_from = {}
        self.g_score = {}
        self.f_score = {}

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
        """Controla trocas de modal para evitar veículo próprio quando inicia a pé."""
        if current_modal == next_modal:
            return True

        if start_modal == "walk":
            # Ao iniciar a pe, permite embarque em meios publicos/app.
            if current_modal == "walk" and next_modal in {
                "walk",
                "bus",
                "uber_car",
                "uber_moto",
                "bike",
            }:
                return True

            # Permite desembarque para finalizar percurso a pe.
            if current_modal in {"bus", "uber_car", "uber_moto", "bike"}:
                return next_modal == "walk"

            return False

        return True

    def heuristic(
        self, current: Tuple[int, str], goal: Tuple[int, str], speed_getter
    ) -> float:
        """
        Heurística: distância euclidiana em linha reta / velocidade máxima.

        Args:
            current: (node, modal)
            goal: (node, modal)
            speed_getter: Função para obter velocidade de um modal

        Returns:
            Valor heurístico
        """
        node_curr, modal_curr = current
        node_goal, _ = goal

        try:
            curr_data = self.graph.nodes[node_curr]
            goal_data = self.graph.nodes[node_goal]

            lat1 = curr_data.get("y", 0)
            lon1 = curr_data.get("x", 0)

            lat2 = goal_data.get("y", 0)
            lon2 = goal_data.get("x", 0)

            # Distância euclidiana aproximada (em graus * 111 km/grau)
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            distance_km = math.sqrt(dlat**2 + dlon**2) * 111

            # Usa velocidade máxima disponível
            max_speed = max(
                speed_getter(m)
                for m in ["walk", "bike", "car", "moto", "bus", "uber_car", "uber_moto"]
            )
            time = distance_km / max_speed if max_speed > 0 else distance_km

            # Normaliza
            time_norm = Normalizer.normalize_value(
                time,
                self.normalizer_params["time"]["min"],
                self.normalizer_params["time"]["max"],
            )

            return time_norm * 100  # Multiplica por 100 para melhor escala

        except Exception as e:
            return 0

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
        Calcula tempo, custo e risco de uma aresta.

        Returns:
            (tempo_normalizado, custo_normalizado, risco_normalizado)
        """

        try:
            # Encontra aresta com esse modal
            edge_data = None
            if self.graph.has_edge(u, v):
                for key, data in self.graph[u][v].items():
                    if data.get("modal") == modal:
                        edge_data = data
                        break

            if edge_data is None:
                return (float("inf"), float("inf"), float("inf"))

            distance_km = edge_data.get("distance_km", 0)

            # Calcula tempo
            speed = self._resolve_edge_speed(edge_data, modal, speed_getter)
            tempo_base = distance_km / speed if speed > 0 else 10
            tempo_final = tempo_base * rain_factor * tide_factor

            time_minutes = tempo_final * 60

            # Calcula custo
            custo_rota = cost_calc.calculate_routing_cost(
                modal,
                distance_km,
                time_minutes=time_minutes,
                avg_speed_kmh=speed,
                rain_factor=rain_factor,
                tide_factor=tide_factor,
            )

            # Calcula risco com segurança por modal e fator de clima
            climate_factor = rain_factor * tide_factor
            risco_base = risk_calc.get_adjusted_risk(modal, climate_factor)
            risco = risco_base * distance_km / 10  # Escala pelo acúmulo

            # Normaliza
            tempo_norm = Normalizer.normalize_value(
                tempo_final,
                self.normalizer_params["time"]["min"],
                self.normalizer_params["time"]["max"],
            )

            custo_norm = Normalizer.normalize_value(
                custo_rota,
                self.normalizer_params["cost"]["min"],
                self.normalizer_params["cost"]["max"],
            )

            risco_norm = Normalizer.normalize_value(
                risco,
                self.normalizer_params["risk"]["min"],
                self.normalizer_params["risk"]["max"],
            )

            return (tempo_norm, custo_norm, risco_norm)

        except Exception as e:
            print(f"Erro ao calcular custo de aresta: {e}")
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
        allowed_modes: set[str] | None = None,
        bus_required: bool = False,
        max_walk_distance_km: float | None = None,
        walk_penalty_factor: float = 1.0,
    ) -> Optional[List[Tuple[int, str]]]:
        """
        Executa A* para encontrar o caminho ótimo.

        Args:
            start: (node_inicial, modal_inicial)
            goal: (node_destino, modal_destino)
            cost_calc: Calculador de custos
            risk_calc: Calculador de riscos
            rain_factor: Fator multiplicativo de chuva
            tide_factor: Fator multiplicativo de maré
            speed_getter: Função que retorna velocidade (modal) -> float

        Returns:
            Caminho como lista de estados (node, modal)
        """

        if speed_getter is None:
            speed_getter = lambda m: 10

        if start_modal is None:
            start_modal = start[1]

        allowed_modes_norm = None
        if allowed_modes:
            allowed_modes_norm = {m.lower() for m in allowed_modes}

        start_used_bus = start[1].lower() == "bus"
        start_state = (start[0], start[1], start_used_bus)

        self.closed_set = set()
        self.open_set = {start_state}
        self.came_from = {}
        self.g_score = {start_state: 0}

        h_start = self.heuristic(start, goal, speed_getter)
        self.f_score = {start_state: h_start}

        pq = [(h_start, start_state)]  # (f_score, state)

        iteration = 0
        max_iterations = 100000

        while self.open_set and iteration < max_iterations:
            iteration += 1

            # Remove elemento com menor f_score
            _, current = heapq.heappop(pq)

            if current not in self.open_set:
                continue

            self.open_set.remove(current)
            self.closed_set.add(current)

            # Verifica se chegou ao destino
            if current[0] == goal[0] and (not bus_required or current[2]):
                return self._reconstruct_path(current)

            node_curr, modal_curr, used_bus_curr = current

            # Expande vizinhos
            for neighbor in self.graph.neighbors(node_curr):
                for key, edge_data in self.graph[node_curr][neighbor].items():
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

                    # Calcula custo da transição
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

                    # Função objetivo multiobjetiva
                    weight = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
                    if modal_neighbor == "walk" and walk_penalty_factor != 1.0:
                        weight *= walk_penalty_factor

                    tentative_g = self.g_score.get(current, float("inf")) + weight

                    if (
                        state_neighbor not in self.g_score
                        or tentative_g < self.g_score[state_neighbor]
                    ):
                        self.came_from[state_neighbor] = current
                        self.g_score[state_neighbor] = tentative_g

                        h = self.heuristic((neighbor, modal_neighbor), goal, speed_getter)
                        f = tentative_g + h
                        self.f_score[state_neighbor] = f

                        if state_neighbor not in self.open_set:
                            self.open_set.add(state_neighbor)
                            heapq.heappush(pq, (f, state_neighbor))

        print(f"A* não encontrou caminho após {iteration} iterações")
        return None

    def _reconstruct_path(self, current: Tuple[int, str, bool]) -> List[Tuple[int, str]]:
        """Reconstrói o caminho a partir do mapa de precedentes."""
        path = [current]
        while current in self.came_from:
            current = self.came_from[current]
            path.append(current)
        path.reverse()
        return [(node, modal) for node, modal, _ in path]
