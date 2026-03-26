import numpy as np
from typing import Dict, List


class Normalizer:
    """Normaliza valores usando Min-Max normalization."""

    def __init__(self):
        self.temps = []
        self.costs = []
        self.risks = []

    def register_values(self, tempo: float, custo: float, risco: float):
        """Registra valores para calcular minmax mais tarde."""
        self.temps.append(tempo)
        self.costs.append(custo)
        self.risks.append(risco)

    def normalize(self) -> Dict[str, Dict[str, float]]:
        """Calcula fatores de normalização Min-Max."""

        temps_array = np.array(self.temps)
        costs_array = np.array(self.costs)
        risks_array = np.array(self.risks)

        return {
            "time": {
                "min": float(temps_array.min()),
                "max": float(temps_array.max()),
                "range": float(temps_array.max() - temps_array.min()),
            },
            "cost": {
                "min": float(costs_array.min()),
                "max": float(costs_array.max()),
                "range": float(costs_array.max() - costs_array.min()),
            },
            "risk": {
                "min": float(risks_array.min()),
                "max": float(risks_array.max()),
                "range": float(risks_array.max() - risks_array.min()),
            },
        }

    @staticmethod
    def normalize_value(value: float, min_val: float, max_val: float) -> float:
        """Aplica normalização Min-Max a um valor individual."""
        range_val = max_val - min_val

        if range_val == 0:
            return 0.5  # Valor médio se não há variação

        normalized = (value - min_val) / range_val
        return max(0, min(1, normalized))  # Clipa para [0, 1]
