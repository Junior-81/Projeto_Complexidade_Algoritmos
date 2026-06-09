"""Calculo do risco de uma aresta, por modal.

Risco combina dois fatores, cada um com peso 50%, vindos do banco:
  * crime    -> roubos registrados por modal (crime_rate), normalizados pelo
                maior valor entre os modais -> intensidade em [0, 1];
  * acidente -> mortes / envolvidos por modal (accident_rate) -> razao em [0, 1].

`risk_intensity(mode)` devolve essa intensidade combinada (0..1), usada pelo
`routing_service` para penalizar o peso de busca. `risk_for_mode(mode, dist)`
escala a intensidade pelo comprimento da aresta (exposicao), compondo o score de
risco reportado em cada `Edge`.
"""

from __future__ import annotations

CRIME_WEIGHT = 0.5
ACCIDENT_WEIGHT = 0.5


class RiskCalculator:
    """Compoe o risco de transitar por uma aresta de determinado modal."""

    def __init__(
        self,
        crime_by_mode: dict[str, int] | None = None,
        accident_by_mode: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        # crime_by_mode: modal -> roubos.
        self.crime_by_mode = crime_by_mode or {}
        # accident_by_mode: modal -> (mortes, envolvidos).
        self.accident_by_mode = accident_by_mode or {}
        # Maior numero de roubos entre os modais (normalizador do crime).
        self._max_robberies = max(self.crime_by_mode.values(), default=0) or 1

    def risk_intensity(self, mode: str) -> float:
        """Intensidade de risco do modal em [0, 1] (independe da distancia)."""
        crime_norm = self.crime_by_mode.get(mode, 0) / self._max_robberies

        deaths, involved = self.accident_by_mode.get(mode, (0, 0))
        accident_ratio = deaths / involved if involved else 0.0

        intensidade = CRIME_WEIGHT * crime_norm + ACCIDENT_WEIGHT * accident_ratio
        # Clampa em [0, 1] por seguranca (ratios anomalos no dataset).
        return max(0.0, min(1.0, intensidade))

    def risk_for_mode(self, mode: str, distance_km: float) -> float:
        """Score de risco da aresta: intensidade do modal escalada pela exposicao."""
        return self.risk_intensity(mode) * distance_km
