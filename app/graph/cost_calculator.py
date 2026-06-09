"""Calculo do custo monetario (R$) de uma aresta, por modal.

Custo depende do modal e usa os fatores reais carregados do banco:
  * combustivel (car/moto) -> distancia / km_per_liter * preco do litro
    + fixed_cost_per_km * distancia            (fuel_consumption);
  * bike                   -> fixed_cost_per_km * distancia (amortizacao);
  * Uber (uber_car/moto)   -> base_fare + tarifa media por km e por minuto
                              (uber_price_ranges, usando o ponto medio da faixa);
  * onibus                 -> tarifa fixa cobrada uma unica vez no embarque;
  * walk                   -> 0.
"""

from __future__ import annotations

# Preco medio do litro de combustivel (R$/L). Nao vem do GTFS/dump, por isso
# fica como parametro de configuracao com um default realista para a RMR.
FUEL_PRICE_BRL_PER_LITER = 6.0


class CostCalculator:
    """Compoe o custo monetario de uma aresta de determinado modal."""

    def __init__(
        self,
        fuel_by_mode: dict[str, dict[str, float]] | None = None,
        uber_config: dict[str, dict[str, float]] | None = None,
        bus_fare: float = 4.50,
        fuel_price: float = FUEL_PRICE_BRL_PER_LITER,
    ) -> None:
        # fuel_by_mode: modal -> {"km_per_liter": x, "fixed_cost_per_km": y}.
        self.fuel_by_mode = fuel_by_mode or {}
        # uber_config: service -> faixas de tarifa (base/km/min).
        self.uber_config = uber_config or {}
        self.bus_fare = bus_fare
        self.fuel_price = fuel_price

    def cost_for_mode(
        self, mode: str, distance_km: float, duration_min: float
    ) -> float:
        """Retorna o custo (R$) de uma aresta de `mode`.

        Onibus tem custo de *deslocamento* zero: a tarifa fixa e cobrada uma vez
        no embarque via `bus_boarding_fare`, pelo `routing_service`.
        """
        if mode in ("uber_car", "uber_moto"):
            return self._uber_cost(mode, distance_km, duration_min)
        if mode == "bus":
            return 0.0
        return self._fuel_cost(mode, distance_km)

    def bus_boarding_fare(self) -> float:
        """Tarifa fixa do onibus, cobrada uma vez por embarque."""
        return self.bus_fare

    # -- internos ----------------------------------------------------------

    def _fuel_cost(self, mode: str, distance_km: float) -> float:
        """Custo de combustivel + custo fixo por km (car/moto/bike/walk)."""
        params = self.fuel_by_mode.get(mode)
        if not params:
            return 0.0
        km_per_liter = params.get("km_per_liter", 0.0)
        fixed = params.get("fixed_cost_per_km", 0.0)
        fuel = (distance_km / km_per_liter) * self.fuel_price if km_per_liter else 0.0
        return fuel + fixed * distance_km

    def _uber_cost(self, mode: str, distance_km: float, duration_min: float) -> float:
        """base_fare + tarifa media por km e por minuto (ponto medio da faixa)."""
        cfg = self.uber_config.get(mode)
        if not cfg:
            return 0.0
        per_km = (cfg.get("km_min", 0.0) + cfg.get("km_max", 0.0)) / 2
        per_min = (cfg.get("min_min", 0.0) + cfg.get("min_max", 0.0)) / 2
        return cfg.get("base_fare", 0.0) + per_km * distance_km + per_min * duration_min
