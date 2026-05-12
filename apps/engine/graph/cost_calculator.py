import pandas as pd
from typing import Dict
from datetime import datetime


WALK_EFFORT_FACTOR = 5.0
BIKE_EFFORT_FACTOR = 1.5


class CostCalculator:
    """Calcula custos de transporte por modal."""

    def __init__(
        self,
        fuel_df: pd.DataFrame,
        uber_df: pd.DataFrame,
        speed_df: pd.DataFrame,
        gas_price: float = 5.50,
        walk_effort_factor: float = WALK_EFFORT_FACTOR,
        bike_effort_factor: float = BIKE_EFFORT_FACTOR,
        debug_walk_penalty: bool = False,
        debug_bike_penalty: bool = False,
    ):
        self.fuel_df = fuel_df if fuel_df is not None else pd.DataFrame()
        self.uber_df = uber_df if uber_df is not None else pd.DataFrame()
        self.speed_df = speed_df if speed_df is not None else pd.DataFrame()

        self.gas_price = gas_price  # R$ por litro
        self.walk_effort_factor = walk_effort_factor
        self.bike_effort_factor = bike_effort_factor
        self.debug_walk_penalty = debug_walk_penalty
        self.debug_bike_penalty = debug_bike_penalty

        # Valores ajustados com base no achado informado.
        self.uber_config = {
            "uber_car": {
                "base": 3.00,
                "km_min": 1.10,
                "km_max": 1.60,
                "min_min": 0.20,
                "min_max": 0.40,
            },
            "uber_moto": {
                "base": 2.00,
                "km_min": 0.60,
                "km_max": 1.00,
                "min_min": 0.05,
                "min_max": 0.20,
            },
        }

    @staticmethod
    def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        return max(min_val, min(max_val, value))

    def _get_car_cost(self) -> float:
        """Extrai custo do carro a partir dos dados de combustível."""
        if not self.fuel_df.empty:
            mode_col = "mode" if "mode" in self.fuel_df.columns else "modal"
            car_row = self.fuel_df[self.fuel_df[mode_col].str.lower() == "car"]
            if not car_row.empty:
                return float(car_row.iloc[0].get("km_per_liter", 8.0))
        return 8.0

    def _get_moto_cost(self) -> float:
        """Extrai custo da moto a partir dos dados de combustível."""
        if not self.fuel_df.empty:
            mode_col = "mode" if "mode" in self.fuel_df.columns else "modal"
            moto_row = self.fuel_df[self.fuel_df[mode_col].str.lower() == "moto"]
            if not moto_row.empty:
                return float(moto_row.iloc[0].get("km_per_liter", 35.0))
        return 35.0

    def _get_bike_cost(self) -> float:
        """Extrai custo da bike a partir dos dados de combustível."""
        if not self.fuel_df.empty:
            mode_col = "mode" if "mode" in self.fuel_df.columns else "modal"
            bike_row = self.fuel_df[self.fuel_df[mode_col].str.lower() == "bike"]
            if not bike_row.empty:
                return float(bike_row.iloc[0].get("fixed_cost_per_km", 0.01))
        return 0.01

    def _dynamic_uber_rates(
        self,
        modal: str,
        avg_speed_kmh: float,
        rain_factor: float,
        traffic_factor: float | None = None,
        driver_supply_factor: float | None = None,
    ) -> Dict[str, float]:
        """Calcula tarifas por km e por minuto dentro da faixa dinâmica do Uber."""
        cfg = self.uber_config.get(modal, self.uber_config["uber_car"])

        # Clima mais severo aumenta preço.
        weather_weight = self._clamp(((rain_factor - 1.0) / 1.5))

        # Trânsito inferido por velocidade média observada (quanto menor, pior).
        if traffic_factor is None:
            ref_speed = 50.0 if modal == "uber_car" else 45.0
            traffic_weight = self._clamp(1.0 - (avg_speed_kmh / ref_speed))
        else:
            traffic_weight = self._clamp(traffic_factor)

        # Oferta de motoristas aproximada por horário de pico.
        if driver_supply_factor is None:
            hour = datetime.now().hour
            is_peak = (6 <= hour <= 9) or (17 <= hour <= 20)
            supply_weight = 0.7 if is_peak else 0.4
        else:
            supply_weight = self._clamp(driver_supply_factor)

        surge_index = self._clamp(
            0.35 * weather_weight + 0.45 * traffic_weight + 0.20 * supply_weight
        )

        price_per_km = cfg["km_min"] + surge_index * (cfg["km_max"] - cfg["km_min"])
        price_per_min = cfg["min_min"] + surge_index * (cfg["min_max"] - cfg["min_min"])

        return {
            "base": cfg["base"],
            "price_per_km": price_per_km,
            "price_per_min": price_per_min,
        }

    def calculate_financial_cost(
        self,
        modal: str,
        distance_km: float,
        time_minutes: float = 0.0,
        avg_speed_kmh: float = 50.0,
        rain_factor: float = 1.0,
        traffic_factor: float | None = None,
        driver_supply_factor: float | None = None,
    ) -> float:
        """
        Calcula o custo para um modal específico.

        Args:
            modal: Modo de transporte
            distance_km: Distância em km
            time_minutes: Tempo do trecho em minutos
            avg_speed_kmh: Velocidade média usada para inferir trânsito
            rain_factor: Fator de clima
            traffic_factor: Nível de trânsito [0, 1] (opcional)
            driver_supply_factor: Nível de oferta de motoristas [0, 1] (opcional)

        Returns:
            Custo financeiro em reais
        """
        modal = modal.lower()

        if modal == "uber":
            modal = "uber_car"

        if modal == "walk":
            return 0.0

        elif modal == "bike":
            bike_operational_cost = distance_km * self._get_bike_cost()
            return bike_operational_cost

        elif modal == "bus":
            return 4.50  # Tarifa fixa

        elif modal == "car":
            km_per_liter = self._get_car_cost()
            liters = distance_km / km_per_liter
            return liters * self.gas_price

        elif modal == "moto":
            km_per_liter = self._get_moto_cost()
            liters = distance_km / km_per_liter
            return liters * self.gas_price

        elif modal in {"uber_car", "uber_moto"}:
            rates = self._dynamic_uber_rates(
                modal,
                avg_speed_kmh=avg_speed_kmh,
                rain_factor=rain_factor,
                traffic_factor=traffic_factor,
                driver_supply_factor=driver_supply_factor,
            )
            return (
                rates["base"]
                + (distance_km * rates["price_per_km"])
                + (time_minutes * rates["price_per_min"])
            )

        else:
            return 0

    def calculate_effort_score(
        self,
        modal: str,
        distance_km: float,
        climate_factor: float = 1.0,
    ) -> float:
        """Calcula esforço físico (cansaço) em pontos, sem unidade monetária."""
        modal = modal.lower()

        climate_adjustment = max(1.0, float(climate_factor))

        if modal == "walk":
            effort = distance_km * self.walk_effort_factor * climate_adjustment
            if self.debug_walk_penalty:
                print(
                    f"[DEBUG] Walk effort aplicada: {effort:.4f} para {distance_km:.4f} km"
                )
            return effort

        if modal == "bike":
            effort = distance_km * self.bike_effort_factor * climate_adjustment
            if self.debug_bike_penalty:
                print(
                    f"[DEBUG] Bike effort aplicada: {effort:.4f} para {distance_km:.4f} km"
                )
            return effort

        return 0.0

    def calculate_routing_cost(
        self,
        modal: str,
        distance_km: float,
        time_minutes: float = 0.0,
        avg_speed_kmh: float = 50.0,
        rain_factor: float = 1.0,
        tide_factor: float = 1.0,
        traffic_factor: float | None = None,
        driver_supply_factor: float | None = None,
        effort_weight: float = 1.0,
    ) -> float:
        """Custo usado no roteamento: financeiro + peso de esforço."""
        financial_cost = self.calculate_financial_cost(
            modal,
            distance_km,
            time_minutes=time_minutes,
            avg_speed_kmh=avg_speed_kmh,
            rain_factor=rain_factor,
            traffic_factor=traffic_factor,
            driver_supply_factor=driver_supply_factor,
        )
        effort_score = self.calculate_effort_score(
            modal,
            distance_km,
            climate_factor=rain_factor * tide_factor,
        )
        return financial_cost + (effort_weight * effort_score)

    def calculate_cost(
        self,
        modal: str,
        distance_km: float,
        time_minutes: float = 0.0,
        avg_speed_kmh: float = 50.0,
        rain_factor: float = 1.0,
        traffic_factor: float | None = None,
        driver_supply_factor: float | None = None,
    ) -> float:
        """Compatibilidade: mantém assinatura antiga retornando custo financeiro."""
        return self.calculate_financial_cost(
            modal,
            distance_km,
            time_minutes=time_minutes,
            avg_speed_kmh=avg_speed_kmh,
            rain_factor=rain_factor,
            traffic_factor=traffic_factor,
            driver_supply_factor=driver_supply_factor,
        )

    def get_all_costs(self, distance_km: float) -> Dict[str, float]:
        """Retorna custos para todos os modais."""
        return {
            modal: self.calculate_financial_cost(modal, distance_km)
            for modal in [
                "walk",
                "bike",
                "car",
                "moto",
                "bus",
                "uber_car",
                "uber_moto",
            ]
        }
