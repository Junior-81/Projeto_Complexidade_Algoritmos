"""Busca dos multiplicadores de peso dinamico no PostgreSQL.

O custo real de transitar de um no A para B nao e apenas a distancia: depende de
multiplicadores de crime, alagamento, clima/mare e da velocidade do modal. Este
servico consulta esses fatores no banco.

Edge case "Fallback de Banco": se o PostgreSQL estiver indisponivel, qualquer
excecao de banco e capturada e o servico retorna **pesos neutros (1.0)** em vez
de propagar um erro 500, permitindo que a rota continue sendo calculada.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.entities.db_models import (
    AccidentRate,
    CrimeRate,
    FloodRiskStreet,
    TransportSpeed,
)

logger = logging.getLogger(__name__)

# Velocidade de fallback (km/h) quando o banco nao responde, por modal.
_DEFAULT_SPEED_KMH: dict[str, float] = {
    "walk": 5.0,
    "bike": 15.0,
    "bus": 25.0,
    "car": 40.0,
    "moto": 45.0,
    "uber_car": 35.0,
    "uber_moto": 40.0,
}


@dataclass
class EdgeMultipliers:
    """Multiplicadores aplicados ao peso de uma aresta."""

    speed_kmh: float
    crime_factor: float
    accident_factor: float
    flood_rain_multiplier: float
    flood_tide_multiplier: float
    from_fallback: bool = False


def _neutral_multipliers(mode: str) -> EdgeMultipliers:
    """Pesos neutros usados quando o banco esta indisponivel."""
    return EdgeMultipliers(
        speed_kmh=_DEFAULT_SPEED_KMH.get(mode, 30.0),
        crime_factor=1.0,
        accident_factor=1.0,
        flood_rain_multiplier=1.0,
        flood_tide_multiplier=1.0,
        from_fallback=True,
    )


def get_edge_multipliers(
    session: Session, mode: str, street_name: str | None = None
) -> EdgeMultipliers:
    """Le velocidade, crime, acidente e alagamento para uma aresta.

    Retorna sempre um `EdgeMultipliers` valido: em caso de falha de banco, usa
    valores neutros (`from_fallback=True`) e registra um warning.
    """
    try:
        speed_row = session.exec(
            select(TransportSpeed).where(TransportSpeed.mode == mode)
        ).first()
        speed_kmh = speed_row.speed_kmh if speed_row else _DEFAULT_SPEED_KMH.get(mode, 30.0)

        crime_row = session.exec(
            select(CrimeRate).where(CrimeRate.mode == mode)
        ).first()
        # Mantemos o valor bruto; a normalizacao fica no RiskCalculator.
        crime_factor = float(crime_row.robberies) if crime_row else 1.0

        accident_row = session.exec(
            select(AccidentRate).where(AccidentRate.mode == mode)
        ).first()
        accident_factor = (
            accident_row.deaths / accident_row.involved
            if accident_row and accident_row.involved
            else 1.0
        )

        rain_mult, tide_mult = 1.0, 1.0
        if street_name:
            flood_row = session.exec(
                select(FloodRiskStreet).where(FloodRiskStreet.street_name == street_name)
            ).first()
            if flood_row:
                rain_mult = flood_row.rain_multiplier
                tide_mult = flood_row.tide_multiplier

        return EdgeMultipliers(
            speed_kmh=speed_kmh,
            crime_factor=crime_factor,
            accident_factor=accident_factor,
            flood_rain_multiplier=rain_mult,
            flood_tide_multiplier=tide_mult,
        )
    except SQLAlchemyError as exc:
        logger.warning(
            "PostgreSQL indisponivel ao buscar pesos do modal '%s'; "
            "usando pesos neutros. Detalhe: %s",
            mode,
            exc,
        )
        return _neutral_multipliers(mode)
