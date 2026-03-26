import requests
from typing import Dict, Any, Tuple
import urllib.parse


class WeatherAPI:
    """Obtém dados climáticos via API."""

    def __init__(self):
        # Usando Open-Meteo API (gratuita, sem chave)
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Obtém dados climáticos para uma localização.

        Args:
            latitude: Latitude em graus decimais
            longitude: Longitude em graus decimais

        Returns:
            Dict com informações de chuva e fatores de multiplicação
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "precipitation,rain",
                "hourly": "precipitation",
                "timezone": "auto",
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extrai precipitação atual
            current = data.get("current", {})
            precipitation = current.get("precipitation", 0)
            rain = current.get("rain", 0)

            # Determina fator de chuva
            rain_factor = self._get_rain_factor(precipitation)

            return {
                "precipitation": precipitation,
                "rain": rain,
                "rain_factor": rain_factor,
                "status": "success",
            }

        except Exception as e:
            print(f"Erro ao obter clima: {e}")
            # Retorna valores padrão (sem chuva)
            return {
                "precipitation": 0,
                "rain": False,
                "rain_factor": 1.0,
                "status": "error",
                "error": str(e),
            }

    def _get_rain_factor(self, precipitation: float) -> float:
        """Converte precipitação em fator multiplicativo."""
        if precipitation == 0:
            return 1.0
        elif precipitation < 2.5:
            return 1.2  # Chuva leve
        elif precipitation < 10:
            return 1.5  # Chuva moderada
        elif precipitation < 50:
            return 2.0  # Chuva pesada
        else:
            return 2.5  # Tempestade

    def get_tide_factor(self, latitude: float, longitude: float) -> float:
        """
        Obtém estimativa de fator de maré.
        Para simplificar, usa uma heurística baseada na hora.

        Em um sistema real, consultaria uma API de marés.
        """
        from datetime import datetime

        hour = datetime.now().hour

        # Simples heurística: maré varia durante o dia
        # Marés ocorrem a cada ~6h12m
        tide_phase = (hour % 12) / 12

        if 0.2 < tide_phase < 0.3 or 0.7 < tide_phase < 0.8:
            return 1.5  # Maré muito alta
        elif 0.1 < tide_phase < 0.4 or 0.6 < tide_phase < 0.9:
            return 1.3  # Maré alta
        elif 0.4 < tide_phase < 0.6:
            return 1.1  # Maré normal
        else:
            return 1.0  # Maré baixa
