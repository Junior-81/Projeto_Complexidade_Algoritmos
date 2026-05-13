"""Cache em disco do grafo multimodal + speed_data, validado por hash.

Substitui o antigo `graph_cache_utils.py` e a lógica embutida em `graph_builder.py`.
"""

from __future__ import annotations

import hashlib
import pickle
from typing import Dict, Optional, Tuple

import networkx as nx

from core.config import CACHE_DIR, DATA_DIR

_GRAPH_FILE = CACHE_DIR / "multimodal_graph.pkl"
_META_FILE = CACHE_DIR / "graph_meta.txt"


def _compute_data_hash() -> str:
    """Hash MD5 dos arquivos de `data/` (CSVs + GTFS) — invalida cache quando dados mudam."""
    hash_obj = hashlib.md5()
    if not DATA_DIR.exists():
        return "no_data_dir"

    for pattern in ("*.csv", "bus_gtfs/*"):
        for file in sorted(DATA_DIR.glob(pattern)):
            if not file.is_file():
                continue
            try:
                with open(file, "rb") as f:
                    hash_obj.update(f.read()[:10_000])
            except OSError:
                pass
    return hash_obj.hexdigest()[:16]


def save(graph: nx.MultiDiGraph, speed_data: Dict) -> bool:
    """Persiste grafo + speed_data com hash dos dados de entrada."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data_hash = _compute_data_hash()
        with open(_GRAPH_FILE, "wb") as f:
            pickle.dump({"graph": graph, "speed_data": speed_data}, f)
        _META_FILE.write_text(data_hash)
        print(f"✓ Grafo cacheado (hash={data_hash})")
        return True
    except Exception as exc:
        print(f"⚠ Falha ao cachear grafo: {exc}")
        return False


def load() -> Optional[Tuple[nx.MultiDiGraph, Dict]]:
    """Carrega grafo cacheado se hash bater com o estado atual de `data/`."""
    if not (_GRAPH_FILE.exists() and _META_FILE.exists()):
        return None

    try:
        cached_hash = _META_FILE.read_text().strip()
        current_hash = _compute_data_hash()
        if cached_hash != current_hash:
            print(f"⚠ Cache invalido (hash mudou: {cached_hash} -> {current_hash})")
            return None

        with open(_GRAPH_FILE, "rb") as f:
            data = pickle.load(f)
        print(f"✓ Grafo carregado do cache (hash={cached_hash})")
        return data["graph"], data["speed_data"]
    except Exception as exc:
        print(f"⚠ Falha ao carregar cache: {exc}")
        return None
