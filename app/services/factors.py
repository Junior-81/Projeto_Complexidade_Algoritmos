import logging
import pandas as pd

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.entities.db_models import (
    AccidentRate,
    BusStop,
    CrimeRate,
    FuelConsumption,
    TransportSpeed,
    UberPriceRange,
)

logger = logging.getLogger(__name__)

# Segmentos = pares de paradas consecutivas em cada viagem, DEDUPLICADOS
# (3M pares -> ~9,7k unicos). O rotulo da linha vem do route_short_name.
_BUS_SEGMENTS_SQL = text(
    """
    WITH seq AS (
        SELECT
            bst.trip_id,
            bst.stop_id AS from_stop,
            LEAD(bst.stop_id) OVER (
                PARTITION BY bst.trip_id ORDER BY bst.stop_sequence
            ) AS to_stop
        FROM bus_stop_times bst
    )
    SELECT seq.from_stop, seq.to_stop, MIN(r.route_short_name) AS line
    FROM seq
    JOIN bus_trips t ON t.trip_id = seq.trip_id
    LEFT JOIN bus_routes r ON r.route_id = t.route_id
    WHERE seq.to_stop IS NOT NULL AND seq.from_stop <> seq.to_stop
    GROUP BY seq.from_stop, seq.to_stop
    """
)


def load_factor_frames(session: Session) -> dict[str, pd.DataFrame]:
    try:
        speed = session.exec(select(TransportSpeed)).all()
        crime = session.exec(select(CrimeRate)).all()
        accident = session.exec(select(AccidentRate)).all()
        fuel = session.exec(select(FuelConsumption)).all()
        uber = session.exec(select(UberPriceRange)).all()

        return {
            "speed": pd.DataFrame(
                [{"mode": r.mode, "speed_kmh": r.speed_kmh} for r in speed]
            ),
            "crime": pd.DataFrame(
                [{"mode": r.mode, "robberies": r.robberies} for r in crime]
            ),
            "accident": pd.DataFrame(
                [
                    {"mode": r.mode, "deaths": r.deaths, "involved": r.involved}
                    for r in accident
                ]
            ),
            "fuel": pd.DataFrame(
                [
                    {
                        "mode": r.mode,
                        "km_per_liter": r.km_per_liter,
                        "fixed_cost_per_km": r.fixed_cost_per_km,
                    }
                    for r in fuel
                ]
            ),
            "uber": pd.DataFrame(
                [
                    {
                        "service": r.service,
                        "base_fare": r.base_fare,
                        "km_min": r.km_min,
                        "km_max": r.km_max,
                        "min_min": r.min_min,
                        "min_max": r.min_max,
                    }
                    for r in uber
                ]
            ),
        }
    except SQLAlchemyError as exc:
        logger.warning(
            "PostgreSQL indisponivel ao carregar fatores; usando DataFrames "
            "vazios (defaults dos calculators). Detalhe: %s",
            exc,
        )
        return {
            "speed": pd.DataFrame(),
            "crime": pd.DataFrame(),
            "accident": pd.DataFrame(),
            "fuel": pd.DataFrame(),
            "uber": pd.DataFrame(),
        }


def load_bus_network(session: Session) -> dict:
    """Carrega a rede de onibus do Postgres para alimentar o grafo.

    Retorna {"stops": {stop_id: (lat, lon)}, "segments": [(from, to, line), ...]}.
    Se nao houver `bus_stop_times` (tabela vazia) ou o banco falhar, devolve uma
    rede vazia -> o grafo fica so de ruas (onibus indisponivel).
    """
    try:
        segments = [
            (row.from_stop, row.to_stop, row.line)
            for row in session.execute(_BUS_SEGMENTS_SQL)
        ]
        if not segments:
            logger.warning("bus_stop_times vazia: rede de onibus indisponivel.")
            return {"stops": {}, "segments": []}

        stops = {
            s.stop_id: (s.stop_lat, s.stop_lon)
            for s in session.exec(select(BusStop)).all()
            if s.stop_lat is not None and s.stop_lon is not None
        }
        logger.info(
            "Rede de onibus carregada: %d paradas, %d segmentos unicos",
            len(stops), len(segments),
        )
        return {"stops": stops, "segments": segments}
    except SQLAlchemyError as exc:
        logger.warning("Falha ao carregar rede de onibus: %s", exc)
        return {"stops": {}, "segments": []}
