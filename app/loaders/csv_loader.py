"""Ingestao dos CSVs de fatores (e GTFS leve) para o PostgreSQL.

Le os arquivos de `settings.data_dir` (por padrao `data/data`) e popula as
entities correspondentes. O carregamento e idempotente: cada registro e
inserido ou atualizado pela sua chave unica (upsert manual).

Execucao:
    uv run load-data          # via script declarado no pyproject
    uv run python -m app.loaders.csv_loader
"""

import csv
import logging
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, select

from app.config import settings
from app.database import engine, init_db
from app.entities.db_models import (
    AccidentRate,
    BusRoute,
    BusStop,
    BusTrip,
    CrimeRate,
    FloodRiskStreet,
    FuelConsumption,
    TideFactor,
    TransportSpeed,
    UberPriceRange,
    WeatherFactor,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class CSVLoader:
    """Carrega os CSVs de fatores e o GTFS leve para o banco."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir or settings.data_dir)

    # -- helpers -----------------------------------------------------------

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self.data_dir / filename
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _upsert(
        self,
        session: Session,
        model: type[SQLModel],
        key_field: str,
        key_value: Any,
        values: dict[str, Any],
    ) -> None:
        """Insere ou atualiza um registro identificado por `key_field`."""
        existing = session.exec(
            select(model).where(getattr(model, key_field) == key_value)
        ).first()
        if existing:
            for field, value in values.items():
                setattr(existing, field, value)
            session.add(existing)
        else:
            session.add(model(**{key_field: key_value, **values}))

    # -- CSVs de fatores ---------------------------------------------------

    def load_transport_speed(self, session: Session) -> int:
        rows = self._read_csv("transport_speed.csv")
        for r in rows:
            self._upsert(
                session, TransportSpeed, "mode", r["mode"],
                {"speed_kmh": float(r["speed_kmh"])},
            )
        return len(rows)

    def load_crime_rate(self, session: Session) -> int:
        rows = self._read_csv("crime_rate.csv")
        for r in rows:
            self._upsert(
                session, CrimeRate, "mode", r["mode"],
                {"robberies": int(r["robberies"])},
            )
        return len(rows)

    def load_accident_rate(self, session: Session) -> int:
        rows = self._read_csv("accident_rate.csv")
        for r in rows:
            self._upsert(
                session, AccidentRate, "mode", r["mode"],
                {"deaths": int(r["deaths"]), "involved": int(r["involved"])},
            )
        return len(rows)

    def load_fuel_consumption(self, session: Session) -> int:
        rows = self._read_csv("fuel_consumption.csv")
        for r in rows:
            self._upsert(
                session, FuelConsumption, "mode", r["mode"],
                {
                    "km_per_liter": float(r["km_per_liter"]),
                    "fixed_cost_per_km": float(r["fixed_cost_per_km"]),
                },
            )
        return len(rows)

    def load_uber_price_ranges(self, session: Session) -> int:
        rows = self._read_csv("uber_price_ranges.csv")
        for r in rows:
            self._upsert(
                session, UberPriceRange, "service", r["service"],
                {
                    "base_fare": float(r["base_fare"]),
                    "km_min": float(r["km_min"]),
                    "km_max": float(r["km_max"]),
                    "min_min": float(r["min_min"]),
                    "min_max": float(r["min_max"]),
                },
            )
        return len(rows)

    def load_weather_factors(self, session: Session) -> int:
        rows = self._read_csv("weather_factors.csv")
        for r in rows:
            self._upsert(
                session, WeatherFactor, "condition", r["condition"],
                {"factor": float(r["factor"])},
            )
        return len(rows)

    def load_tide_factors(self, session: Session) -> int:
        rows = self._read_csv("tide_factors.csv")
        for r in rows:
            self._upsert(
                session, TideFactor, "tide_level", r["tide_level"],
                {"factor": float(r["factor"])},
            )
        return len(rows)

    def load_flood_risk_streets(self, session: Session) -> int:
        rows = self._read_csv("flood_risk_streets.csv")
        for r in rows:
            self._upsert(
                session, FloodRiskStreet, "street_name", r["street_name"],
                {
                    "rain_multiplier": float(r["rain_multiplier"]),
                    "tide_multiplier": float(r["tide_multiplier"]),
                },
            )
        return len(rows)

    # -- GTFS leve (routes / trips / stops) --------------------------------

    def load_gtfs_light(self, session: Session) -> dict[str, int]:
        """Carrega routes.txt, trips.txt e stops.txt (arquivos leves).

        Nota de escopo: `stop_times.txt` (~3,1 milhoes de linhas) NAO e
        carregado nesta fase. A ingestao em lote desse arquivo sera feita junto
        com a construcao do grafo GTFS.
        """
        gtfs_dir = self.data_dir / "bus_gtfs"
        counts: dict[str, int] = {}

        with (gtfs_dir / "routes.txt").open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
            for r in rows:
                self._upsert(
                    session, BusRoute, "route_id", r["route_id"],
                    {
                        "route_short_name": r.get("route_short_name"),
                        "route_long_name": r.get("route_long_name"),
                        "route_type": int(r["route_type"]) if r.get("route_type") else None,
                    },
                )
            counts["bus_routes"] = len(rows)

        with (gtfs_dir / "stops.txt").open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
            for r in rows:
                self._upsert(
                    session, BusStop, "stop_id", r["stop_id"],
                    {
                        "stop_name": r.get("stop_name"),
                        "stop_lat": float(r["stop_lat"]) if r.get("stop_lat") else None,
                        "stop_lon": float(r["stop_lon"]) if r.get("stop_lon") else None,
                    },
                )
            counts["bus_stops"] = len(rows)

        with (gtfs_dir / "trips.txt").open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
            for r in rows:
                self._upsert(
                    session, BusTrip, "trip_id", r["trip_id"],
                    {
                        "route_id": r["route_id"],
                        "shape_id": r.get("shape_id"),
                        "direction_id": int(r["direction_id"]) if r.get("direction_id") else None,
                        "trip_headsign": r.get("trip_headsign"),
                    },
                )
            counts["bus_trips"] = len(rows)

        return counts

    # -- orquestracao ------------------------------------------------------

    def load_all(self, session: Session, *, include_gtfs: bool = True) -> dict[str, int]:
        """Carrega todos os fatores. Retorna a contagem por dominio."""
        counts: dict[str, int] = {
            "transport_speed": self.load_transport_speed(session),
            "crime_rate": self.load_crime_rate(session),
            "accident_rate": self.load_accident_rate(session),
            "fuel_consumption": self.load_fuel_consumption(session),
            "uber_price_ranges": self.load_uber_price_ranges(session),
            "weather_factors": self.load_weather_factors(session),
            "tide_factors": self.load_tide_factors(session),
            "flood_risk_streets": self.load_flood_risk_streets(session),
        }
        if include_gtfs:
            counts.update(self.load_gtfs_light(session))
        session.commit()
        return counts


def main() -> None:
    """Entry point CLI: cria as tabelas (se preciso) e carrega os dados."""
    init_db()
    loader = CSVLoader()
    with Session(engine) as session:
        counts = loader.load_all(session)
    for domain, n in counts.items():
        logger.info("%-20s %d registros", domain, n)
    logger.info("Carga concluida.")


if __name__ == "__main__":
    main()
