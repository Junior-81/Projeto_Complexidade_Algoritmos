import pandas as pd
import numpy as np
from typing import Dict


class RiskCalculator:
    """Calcula risco por modal baseado em dados de crime e acidentes."""

    SAFETY_MULTIPLIERS = {
        "walk": 1.3,
        "bike": 1.2,
        "moto": 1.4,
        "car": 1.0,
        "bus": 1.2,
        "uber": 1.0,
        "uber_car": 1.0,
        "uber_moto": 1.1,
    }

    def __init__(self, crime_df: pd.DataFrame, accident_df: pd.DataFrame):
        self.crime_df = crime_df
        self.accident_df = accident_df
        self.risk_profiles: Dict[str, float] = {}
        self._calculate_risks()

    def _calculate_risks(self):
        """Calcula riscos para cada modal."""

        # Calcula risco de assalto (crime)
        if not self.crime_df.empty:
            crime_col = "mode" if "mode" in self.crime_df.columns else "modal"
            for _, row in self.crime_df.iterrows():
                modal = row[crime_col].lower()
                robberies = float(row.get("robberies", 0))

                # Normaliza por máximo de roubos
                max_robberies = self.crime_df["robberies"].max()
                crime_risk = robberies / max_robberies if max_robberies > 0 else 0

                if modal not in self.risk_profiles:
                    self.risk_profiles[modal] = 0
                self.risk_profiles[modal] += crime_risk * 0.5  # Peso 50%

        # Calcula risco de acidente
        if not self.accident_df.empty:
            accident_col = "mode" if "mode" in self.accident_df.columns else "modal"
            for _, row in self.accident_df.iterrows():
                modal = row[accident_col].lower()
                deaths = float(row.get("deaths", 0))
                involved = float(row.get("involved", 1))

                if involved > 0:
                    accident_risk = deaths / involved
                else:
                    accident_risk = 0

                if modal not in self.risk_profiles:
                    self.risk_profiles[modal] = 0
                self.risk_profiles[modal] += accident_risk * 0.5  # Peso 50%

        # Normaliza para [0, 1]
        max_risk = max(self.risk_profiles.values()) if self.risk_profiles else 1
        if max_risk > 1:
            for modal in self.risk_profiles:
                self.risk_profiles[modal] /= max_risk

        # Modais padrão com risco baixo
        defaults = {
            "walk": 0.2,
            "bike": 0.25,
            "car": 0.3,
            "moto": 0.35,
            "bus": 0.15,
            "uber": 0.18,
            "uber_car": 0.2,
            "uber_moto": 0.24,
        }

        for modal, default_risk in defaults.items():
            if modal not in self.risk_profiles:
                self.risk_profiles[modal] = default_risk

    def get_risk(self, modal: str) -> float:
        """Retorna risco para um modal específico."""
        return self.risk_profiles.get(modal.lower(), 0.3)

    def get_safety_multiplier(self, modal: str) -> float:
        """Retorna multiplicador de segurança por modal."""
        return self.SAFETY_MULTIPLIERS.get(modal.lower(), 1.0)

    def get_adjusted_risk(self, modal: str, climate_factor: float = 1.0) -> float:
        """Retorna risco com multiplicador por modal e fator de clima."""
        base_risk = self.get_risk(modal)
        modal_multiplier = self.get_safety_multiplier(modal)
        return base_risk * modal_multiplier * climate_factor

    def get_all_risks(self) -> Dict[str, float]:
        """Retorna todos os riscos calculados."""
        return self.risk_profiles.copy()
