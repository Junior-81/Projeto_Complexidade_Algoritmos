"""Schemas Pydantic de entrada e saida do endpoint POST /api/calculate.

O contrato da API e exposto em ingles + camelCase: os campos sao declarados em
ingles `snake_case` (codigo pythonico) e um `alias_generator` converte as chaves
do JSON para camelCase, tanto na entrada quanto na saida. `populate_by_name=True`
permite tambem aceitar os nomes Python diretamente.

A saida reproduz a estrutura `edges` / `segments` / `summary` / `routePoints`.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

# Coordenada [latitude, longitude].
Coordinate = tuple[float, float]

InitialMode = Literal[
    "walk", "bike", "car", "moto", "bus", "uber_car", "uber_moto", "auto"
]

RECIFE_LAT_MIN, RECIFE_LAT_MAX = -8.40, -7.80
RECIFE_LON_MIN, RECIFE_LON_MAX = -35.10, -34.80


def within_region(coord: Coordinate) -> bool:
    """Indica se a coordenada cai dentro do bounding box da RM Recife."""
    lat, lon = coord
    return (
        RECIFE_LAT_MIN <= lat <= RECIFE_LAT_MAX
        and RECIFE_LON_MIN <= lon <= RECIFE_LON_MAX
    )


class CamelModel(BaseModel):
    """Base que serializa/desserializa em camelCase, aceitando tambem snake_case."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class CalculateRequest(CamelModel):
    """Payload de entrada do calculo de rota."""

    origin: Coordinate = Field(..., description="[latitude, longitude] de origem")
    destination: Coordinate = Field(..., description="[latitude, longitude] de destino")
    initial_mode: InitialMode = Field(..., description="Modal de partida")
    # Override opcional da condicao climatica (clear/light_rain/moderate_rain/
    # heavy_rain/storm). Se omitido, o clima atual vem da Open-Meteo.
    weather: str | None = Field(default=None, description="Condicao climatica (override)")

    @field_validator("origin", "destination")
    @classmethod
    def _validate_geographic_range(cls, value: Coordinate) -> Coordinate:
        """Valida que a coordenada e geograficamente plausivel (lat/lon)."""
        lat, lon = value
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("latitude fora do intervalo valido [-90, 90]")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("longitude fora do intervalo valido [-180, 180]")
        return value


# ---------------------------------------------------------------------------
# Saida
# ---------------------------------------------------------------------------


class Edge(CamelModel):
    """Micro-segmento (rua a rua) do trajeto."""

    mode: str
    means: str
    origin: Coordinate
    destination: Coordinate
    distance: float
    time: float
    cost: float
    effort: float
    risk: float
    weight: float
    average_speed_kmh: float
    geometry: list[list[float]]

    # Campos presentes apenas em arestas de onibus (validacao via GTFS).
    line: str | None = None
    gtfs_shape_id: str | None = None
    gtfs_validation: bool | None = None


class Segment(CamelModel):
    """Agrupamento de edges entre trocas de modal, com totais."""

    mode: str
    means: str
    origin: Coordinate
    destination: Coordinate
    time: float
    distance: float
    cost: float
    effort: float
    average_risk: float
    average_speed_kmh: float
    edge_count: int

    # Campos presentes apenas em segmentos de onibus.
    line: str | None = None
    gtfs_shape_id: str | None = None
    gtfs_validation: bool | None = None


class Summary(CamelModel):
    """Totais gerais da viagem."""

    total_time: float
    total_cost: float
    total_effort: float
    total_distance: float
    average_risk: float
    total_average_speed: float


class CalculateResponse(CamelModel):
    """Payload de saida completo do calculo de rota."""

    edges: list[Edge]
    segments: list[Segment]
    summary: Summary
    route_points: list[list[float]]
    # Modal efetivamente escolhido (relevante no modo "auto"); ecoa o pedido nos
    # demais modos. Serializa como `chosenMode`.
    chosen_mode: str | None = None
