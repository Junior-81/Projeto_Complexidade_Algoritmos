"""Constantes globais do motor de roteamento."""

from pathlib import Path

GASOLINE_PRICE_PER_LITER = 7.50

WEIGHTS = {"time": 0.5, "cost": 0.3, "risk": 0.2}

MAX_EDGES_FOR_NORMALIZATION = 80_000

OSMNX_PLACE = "Recife, Brazil"

VALID_ALGORITHMS = {"dijkstra", "astar"}
DEFAULT_ALGORITHM = "dijkstra"

# Paths absolutos: o motor pode ser chamado de qualquer CWD (CLI, backend, etc.).
ENGINE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ENGINE_ROOT / "data"
GTFS_DIR = DATA_DIR / "bus_gtfs"
OUTPUT_DIR = ENGINE_ROOT / "output"
CACHE_DIR = ENGINE_ROOT / "cache"
INPUT_FILE = ENGINE_ROOT / "input.json"
OUTPUT_FILE = OUTPUT_DIR / "output.json"
