from typing import Dict, List


class UberSegmentAggregator:
    """Agrupa arestas sequenciais de Uber como uma corrida continua."""

    def __init__(self, cost_calc, rain_factor: float = 1.0):
        self.cost_calc = cost_calc
        self.rain_factor = rain_factor

    @staticmethod
    def _is_uber(modal: str) -> bool:
        return modal in {"uber", "uber_car", "uber_moto"}

    def apply(self, edges: List[Dict]) -> List[Dict]:
        """
        Atualiza custos de arestas Uber para representar corrida continua.

        O custo total da corrida e atribuido apenas a ultima aresta da sequencia,
        mantendo as demais com custo zero para evitar dupla contagem.
        """
        i = 0
        n = len(edges)

        while i < n:
            modal = edges[i].get("modo", "")
            if not self._is_uber(modal):
                i += 1
                continue

            j = i
            total_distance = 0.0
            total_time_min = 0.0
            speed_samples = []

            while j < n and edges[j].get("modo") == modal:
                total_distance += float(edges[j].get("distancia", 0.0))
                total_time_min += float(edges[j].get("tempo", 0.0)) * 60.0
                speed_samples.append(float(edges[j].get("velocidade_media_kmh", 0.0)))
                edges[j]["custo"] = 0.0
                j += 1

            avg_speed = (
                sum(speed_samples) / len(speed_samples) if speed_samples else 50.0
            )
            total_cost = self.cost_calc.calculate_cost(
                modal,
                total_distance,
                time_minutes=total_time_min,
                avg_speed_kmh=avg_speed,
                rain_factor=self.rain_factor,
            )

            edges[j - 1]["custo"] = round(total_cost, 2)
            i = j

        return edges
