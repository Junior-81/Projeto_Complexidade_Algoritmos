"""Funções puras de geometria e parse de atributos OSM."""

import re
from math import asin, cos, radians, sin, sqrt


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distância em km entre dois pontos lat/lon (graus)."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return c * 6371


def parse_osm_speed_kmh(raw_speed) -> float:
    """Extrai velocidade (km/h) do atributo `maxspeed` do OSM. Fallback: 50 km/h."""
    if raw_speed is None:
        return 50.0

    if isinstance(raw_speed, list) and raw_speed:
        raw_speed = raw_speed[0]

    text = str(raw_speed).lower()
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return 50.0

    value = float(match.group())
    if "mph" in text:
        value *= 1.60934
    return value if value > 0 else 50.0
