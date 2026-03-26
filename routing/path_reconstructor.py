from typing import List, Dict, Any, Tuple

from graph.normalizer import Normalizer
from routing.uber_segment_aggregator import UberSegmentAggregator


class PathReconstructor:
    """Reconstrói rota em arestas detalhadas e segmentos agregados."""

    def __init__(
        self,
        graph,
        cost_calc,
        risk_calc,
        normalizer_params: Dict[str, Dict[str, float]],
        rain_factor: float = 1.0,
        tide_factor: float = 1.0,
        speed_data: Dict[str, float] = None,
    ):
        self.graph = graph
        self.cost_calc = cost_calc
        self.risk_calc = risk_calc
        self.normalizer_params = normalizer_params
        self.rain_factor = rain_factor
        self.tide_factor = tide_factor
        self.speed_data = speed_data or {}

    @staticmethod
    def _resolve_edge_speed(
        edge_data: Dict[str, Any], modal: str, speed_data: Dict[str, float]
    ) -> float:
        """Usa velocidade OSM para motorizados e fallback para os demais."""
        if modal in {"car", "moto", "uber", "uber_car", "uber_moto"}:
            return float(edge_data.get("osm_speed_kmh", 50.0) or 50.0)
        return float(speed_data.get(modal, 10) or 10)

    @staticmethod
    def _edge_label(modal: str) -> str:
        if modal == "uber_car":
            return "uber carro"
        if modal == "uber_moto":
            return "uber moto"
        return modal

    def _build_edge(
        self, node_u: int, node_v: int, modal: str, edge_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monta estrutura detalhada de uma aresta."""
        lat_u = self.graph.nodes[node_u].get("y", 0.0)
        lon_u = self.graph.nodes[node_u].get("x", 0.0)
        lat_v = self.graph.nodes[node_v].get("y", 0.0)
        lon_v = self.graph.nodes[node_v].get("x", 0.0)

        distance_km = float(edge_data.get("distance_km", 0.0))
        speed = self._resolve_edge_speed(edge_data, modal, self.speed_data)

        tempo_base = distance_km / speed if speed > 0 else 10.0
        tempo_final = tempo_base * self.rain_factor * self.tide_factor
        time_minutes = tempo_final * 60

        climate_factor = self.rain_factor * self.tide_factor
        risco_base = self.risk_calc.get_adjusted_risk(modal, climate_factor)
        risco_final = risco_base * distance_km / 10

        # Uber e cobrado por corrida continua, nao por aresta individual.
        if modal in {"uber", "uber_car", "uber_moto"}:
            custo = 0.0
        else:
            custo = self.cost_calc.calculate_cost(
                modal,
                distance_km,
                time_minutes=time_minutes,
                avg_speed_kmh=speed,
                rain_factor=self.rain_factor,
            )

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
            risco_final,
            self.normalizer_params["risk"]["min"],
            self.normalizer_params["risk"]["max"],
        )
        peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm

        edge = {
            "modo": modal,
            "meio": self._edge_label(modal),
            "origem": [lat_u, lon_u],
            "destino": [lat_v, lon_v],
            "distancia": round(distance_km, 4),
            "tempo": round(tempo_final, 4),
            "custo": round(custo, 2),
            "risco": round(risco_final, 4),
            "peso": round(peso, 4),
            "velocidade_media_kmh": round(speed, 2),
        }

        if modal == "bus":
            edge["linha"] = edge_data.get("line") or "N/A"
            edge["gtfs_shape_id"] = edge_data.get("gtfs_shape_id")
            edge["validacao_gtfs"] = bool(edge_data.get("gtfs_shape_id"))
        elif modal in {"uber", "uber_car", "uber_moto"}:
            edge["servico"] = "Uber"

        return edge

    def _build_segments(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Agrupa arestas consecutivas do mesmo modal em segmentos."""
        if not edges:
            return []

        segments: List[Dict[str, Any]] = []
        group = [edges[0]]

        for edge in edges[1:]:
            if edge["modo"] == group[-1]["modo"]:
                group.append(edge)
            else:
                segments.append(self._finalize_segment(group))
                group = [edge]

        segments.append(self._finalize_segment(group))
        return segments

    def _finalize_segment(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolida metadados de um segmento."""
        first = group[0]
        last = group[-1]
        modal = first["modo"]

        distancia = sum(float(e.get("distancia", 0.0)) for e in group)
        tempo = sum(float(e.get("tempo", 0.0)) for e in group)
        custo = sum(float(e.get("custo", 0.0)) for e in group)
        risco_medio = (
            sum(float(e.get("risco", 0.0)) for e in group) / len(group)
            if group
            else 0.0
        )
        vel_media = distancia / tempo if tempo > 0 else 0.0

        segment = {
            "modo": modal,
            "meio": first.get("meio", modal),
            "origem": first.get("origem", [0.0, 0.0]),
            "destino": last.get("destino", [0.0, 0.0]),
            "tempo": round(tempo, 4),
            "distancia": round(distancia, 4),
            "custo": round(custo, 2),
            "risco_medio": round(risco_medio, 4),
            "velocidade_media_kmh": round(vel_media, 2),
            "quantidade_arestas": len(group),
        }

        if modal == "bus":
            segment["linha"] = first.get("linha", "N/A")
            segment["gtfs_shape_id"] = first.get("gtfs_shape_id")
            segment["validacao_gtfs"] = first.get("validacao_gtfs", False)
        elif modal in {"uber", "uber_car", "uber_moto"}:
            segment["servico"] = "Uber"

        return segment

    def _build_summary(self, edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula métricas totais a partir das arestas percorridas."""
        tempo_total = sum(float(e.get("tempo", 0.0)) for e in edges)
        custo_total = sum(float(e.get("custo", 0.0)) for e in edges)
        distancia_total = sum(float(e.get("distancia", 0.0)) for e in edges)
        risco_medio = (
            sum(float(e.get("risco", 0.0)) for e in edges) / len(edges)
            if edges
            else 0.0
        )
        velocidade_media_total = (
            distancia_total / tempo_total if tempo_total > 0 else 0.0
        )

        return {
            "tempo_total": round(tempo_total, 4),
            "custo_total": round(custo_total, 2),
            "distancia_total": round(distancia_total, 4),
            "risco_medio": round(risco_medio, 4),
            "velocidade_media_total": round(velocidade_media_total, 2),
        }

    def reconstruct_route(self, path: List[Tuple[int, str]]) -> Dict[str, Any]:
        """Reconstrói rota em formato detalhado e agregado."""
        edges: List[Dict[str, Any]] = []

        for i in range(len(path) - 1):
            node_curr, _ = path[i]
            node_next, modal_next = path[i + 1]

            if not self.graph.has_edge(node_curr, node_next):
                continue

            selected_edge = None
            for _, data in self.graph[node_curr][node_next].items():
                if data.get("modal") == modal_next:
                    selected_edge = data
                    break

            if selected_edge is None:
                continue

            edges.append(
                self._build_edge(node_curr, node_next, modal_next, selected_edge)
            )

        edges = UberSegmentAggregator(self.cost_calc, self.rain_factor).apply(edges)
        segments = self._build_segments(edges)
        resumo = self._build_summary(edges)

        return {
            "edges": edges,
            "segments": segments,
            "resumo": resumo,
        }
