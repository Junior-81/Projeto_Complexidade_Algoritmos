"""Calculo de custo de uma aresta (STUB).

Custo depende do modal:
  * combustivel -> km_per_liter + fixed_cost_per_km (fuel_consumption);
  * Uber        -> base_fare + tarifa por km/min com surge (uber_price_ranges);
  * onibus      -> tarifa fixa;
  * walk / bike -> tipicamente 0 (ou custo fixo, no caso da bike).
"""


class CostCalculator:
    """Compoe o custo monetario de uma aresta de determinado modal."""

    def __init__(
        self,
        fuel_by_mode: dict[str, dict[str, float]] | None = None,
        uber_config: dict[str, dict[str, float]] | None = None,
        bus_fare: float = 4.50,
    ) -> None:
        # fuel_by_mode: modal -> {"km_per_liter": x, "fixed_cost_per_km": y}.
        self.fuel_by_mode = fuel_by_mode or {}
        # uber_config: hoje hardcoded; sera carregado de uber_price_ranges.
        self.uber_config = uber_config or {}
        self.bus_fare = bus_fare

    def cost_for_mode(
        self, mode: str, distance_km: float, duration_min: float
    ) -> float:
        """Retorna o custo de uma aresta de `mode`.

        TODO: implementar as formulas por modal (combustivel, Uber, onibus).
        """
        raise NotImplementedError("Calculo de custo ainda nao implementado.")
