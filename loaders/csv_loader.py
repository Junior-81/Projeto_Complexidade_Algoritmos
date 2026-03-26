import pandas as pd
import os
from typing import Dict, Any


class CSVLoader:
    """Carrega e gerencia dados de arquivos CSV."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.data: Dict[str, Any] = {}

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Carrega todos os arquivos CSV."""
        csv_files = {
            "crime_rate": "crime_rate.csv",
            "accident_rate": "accident_rate.csv",
            "fuel_consumption": "fuel_consumption.csv",
            "uber_prices": "uber_price_ranges.csv",
            "transport_speed": "transport_speed.csv",
            "flood_risk": "flood_risk_streets.csv",
            "weather_factors": "weather_factors.csv",
            "tide_factors": "tide_factors.csv",
        }

        for key, filename in csv_files.items():
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                self.data[key] = pd.read_csv(filepath)
                print(f"✓ Carregado: {filename}")
            else:
                print(f"✗ Arquivo não encontrado: {filepath}")

        return self.data

    def get(self, key: str) -> pd.DataFrame:
        """Obtém um DataFrame já carregado."""
        return self.data.get(key)
