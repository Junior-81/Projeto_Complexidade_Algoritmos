import json
import logging
import time
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_HTTP_TIMEOUT = 3.0
_CACHE_TTL_SECONDS = 600

_RAIN_SENSITIVITY: dict[str, float] = {
    "walk": 1.0,
    "bike": 1.0,
    "moto": 1.0,
    "uber_moto": 1.0,
    "car": 0.4,
    "uber_car": 0.4,
    "bus": 0.4,
}

_cache: dict[tuple[float, float], tuple[float, str]] = {}


def _classify(precipitation_mm: float) -> str:
    """Converte precipitacao (mm) numa das condicoes da tabela weather_factors."""
    if precipitation_mm <= 0:
        return "clear"
    if precipitation_mm < 2.5:
        return "light_rain"
    if precipitation_mm < 10:
        return "moderate_rain"
    if precipitation_mm < 50:
        return "heavy_rain"
    return "storm"


def get_condition(lat: float, lon: float) -> str:
    """Condicao climatica atual da localizacao (com cache TTL e fallback 'clear')."""
    key = (round(lat, 2), round(lon, 2))
    now = time.time()
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    try:
        query = urllib.parse.urlencode(
            {"latitude": lat, "longitude": lon, "current": "precipitation", "timezone": "auto"}
        )
        with urllib.request.urlopen(f"{_OPEN_METEO_URL}?{query}", timeout=_HTTP_TIMEOUT) as resp:
            data = json.load(resp)
        precipitation = float(data.get("current", {}).get("precipitation", 0) or 0)
        condition = _classify(precipitation)
        logger.info("Open-Meteo: precip=%.1fmm -> condicao=%s", precipitation, condition)
    except Exception as exc:  # noqa: BLE001 - rede instavel nao pode quebrar a rota
        logger.warning("Falha ao obter clima (usando 'clear'): %s", exc)
        condition = "clear"

    _cache[key] = (now + _CACHE_TTL_SECONDS, condition)
    return condition


def effective_rain(mode: str, base_factor: float) -> float:
    """Aplica o fator de chuva com a sensibilidade do modal.

    rain_efetivo = 1 + (base - 1) * sensibilidade[modal]. Em tempestade
    (base=2.5): expostos -> 2.5; protegidos (car/uber_car/bus) -> 1.6.
    """
    sensitivity = _RAIN_SENSITIVITY.get(mode, 1.0)
    return 1.0 + (base_factor - 1.0) * sensitivity
