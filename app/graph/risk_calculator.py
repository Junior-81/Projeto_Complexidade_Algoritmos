"""Calculo de risco de uma aresta (STUB).

Risco combina dois fatores, cada um com peso 50%:
  * crime   -> roubos registrados por modal (crime_rate);
  * acidente -> mortes / envolvidos por modal (accident_rate).

A normalizacao e a escala finais serao definidas na implementacao da matematica.
"""

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

    def risk_for_mode(self, mode: str, distance_km: float) -> float:
        """Retorna o risco de uma aresta de `mode` com dado comprimento.

        TODO: normalizar crime e acidente, aplicar os pesos de 50% e escalar pelo
        comprimento da aresta. Por enquanto e um esqueleto.
        """
        raise NotImplementedError("Calculo de risco ainda nao implementado.")
