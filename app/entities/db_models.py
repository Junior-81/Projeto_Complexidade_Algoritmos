"""Entities do PostgreSQL (SQLModel).

Cada tabela espelha um dos CSVs de `data/data/` ou um arquivo do feed GTFS do
Grande Recife. Esses fatores sao consultados pela camada de servico para compor
o peso dinamico das arestas do grafo (velocidade, risco, custo, alagamento).
"""

from sqlmodel import Field, SQLModel

# ---------------------------------------------------------------------------
# Fatores de TEMPO / velocidade  (transport_speed.csv)
# ---------------------------------------------------------------------------


class TransportSpeed(SQLModel, table=True):
    """Velocidade media por modal em km/h (tempo = distancia / velocidade)."""

    __tablename__ = "transport_speed"

    id: int | None = Field(default=None, primary_key=True)
    mode: str = Field(index=True, unique=True)
    speed_kmh: float


# ---------------------------------------------------------------------------
# Fatores de RISCO  (crime_rate.csv + accident_rate.csv)
# ---------------------------------------------------------------------------


class CrimeRate(SQLModel, table=True):
    """Roubos registrados por modal (risco de assalto, peso 50%)."""

    __tablename__ = "crime_rate"

    id: int | None = Field(default=None, primary_key=True)
    mode: str = Field(index=True, unique=True)
    robberies: int


class AccidentRate(SQLModel, table=True):
    """Acidentes por modal (risco = mortes / envolvidos, peso 50%)."""

    __tablename__ = "accident_rate"

    id: int | None = Field(default=None, primary_key=True)
    mode: str = Field(index=True, unique=True)
    deaths: int
    involved: int


# ---------------------------------------------------------------------------
# Fatores de CUSTO  (fuel_consumption.csv + uber_price_ranges.csv)
# ---------------------------------------------------------------------------


class FuelConsumption(SQLModel, table=True):
    """Eficiencia de combustivel / custo fixo por km, por modal."""

    __tablename__ = "fuel_consumption"

    id: int | None = Field(default=None, primary_key=True)
    mode: str = Field(index=True, unique=True)
    km_per_liter: float
    fixed_cost_per_km: float


class UberPriceRange(SQLModel, table=True):
    """Faixa de tarifa do Uber (base + por km + por minuto, com surge)."""

    __tablename__ = "uber_price_ranges"

    id: int | None = Field(default=None, primary_key=True)
    service: str = Field(index=True, unique=True)
    base_fare: float
    km_min: float
    km_max: float
    min_min: float
    min_max: float


# ---------------------------------------------------------------------------
# Fatores CLIMATICOS / alagamento  (weather_factors.csv, tide_factors.csv,
# flood_risk_streets.csv)
# ---------------------------------------------------------------------------


class WeatherFactor(SQLModel, table=True):
    """Condicao do tempo -> multiplicador (rain_factor)."""

    __tablename__ = "weather_factors"

    id: int | None = Field(default=None, primary_key=True)
    condition: str = Field(index=True, unique=True)
    factor: float


class TideFactor(SQLModel, table=True):
    """Nivel da mare -> multiplicador (tide_factor)."""

    __tablename__ = "tide_factors"

    id: int | None = Field(default=None, primary_key=True)
    tide_level: str = Field(index=True, unique=True)
    factor: float


class FloodRiskStreet(SQLModel, table=True):
    """Ruas que alagam: multiplicador por chuva e por mare."""

    __tablename__ = "flood_risk_streets"

    id: int | None = Field(default=None, primary_key=True)
    street_name: str = Field(index=True, unique=True)
    rain_multiplier: float
    tide_multiplier: float


# ---------------------------------------------------------------------------
# Rede de ONIBUS (GTFS Grande Recife)
# Estrutura basica para rotas, viagens e paradas.
# ---------------------------------------------------------------------------


class BusRoute(SQLModel, table=True):
    """Linha de onibus (routes.txt)."""

    __tablename__ = "bus_routes"

    route_id: str = Field(primary_key=True)
    route_short_name: str | None = None
    route_long_name: str | None = None
    route_type: int | None = None


class BusStop(SQLModel, table=True):
    """Parada de onibus (stops.txt)."""

    __tablename__ = "bus_stops"

    stop_id: str = Field(primary_key=True)
    stop_name: str | None = None
    stop_lat: float | None = None
    stop_lon: float | None = None


class BusTrip(SQLModel, table=True):
    """Viagem de uma linha (trips.txt)."""

    __tablename__ = "bus_trips"

    trip_id: str = Field(primary_key=True)
    route_id: str = Field(foreign_key="bus_routes.route_id", index=True)
    shape_id: str | None = None
    direction_id: int | None = None
    trip_headsign: str | None = None


class BusStopTime(SQLModel, table=True):
    """Horario de uma parada dentro de uma viagem (stop_times.txt).

    Nota de escopo: o arquivo `stop_times.txt` possui ~3,1 milhoes de linhas e
    nao e carregado na fase de setup. A tabela existe para a ingestao em lote
    futura, quando o grafo GTFS for construido de fato.
    """

    __tablename__ = "bus_stop_times"

    id: int | None = Field(default=None, primary_key=True)
    trip_id: str = Field(foreign_key="bus_trips.trip_id", index=True)
    stop_id: str = Field(foreign_key="bus_stops.stop_id", index=True)
    stop_sequence: int
    arrival_time: str | None = None
    departure_time: str | None = None
