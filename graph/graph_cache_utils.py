"""Utilitários para cache de grafos (OSMnx e multimodal)."""

import pickle
from pathlib import Path
from typing import Optional, Tuple, Dict
import networkx as nx
import hashlib


CACHE_DIR = Path(__file__).parent.parent / "output" / ".graph_cache"
CACHE_BASE_GRAPH_FILE = CACHE_DIR / "base_graph_osmnx.pkl"
CACHE_MULTIMODAL_GRAPH_FILE = CACHE_DIR / "multimodal_graph.pkl"
CACHE_META_FILE = CACHE_DIR / "graph_meta.txt"


def save_base_graph_cache(base_graph: nx.DiGraph) -> bool:
    """Salva base_graph do OSMnx em cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_BASE_GRAPH_FILE, "wb") as f:
            pickle.dump(base_graph, f)
        print(f"[CACHE] Base graph (OSMnx) salvo ({len(base_graph.nodes)} nós, {len(base_graph.edges)} arestas)")
        return True
    except Exception as e:
        print(f"[!] Falha ao cachear base_graph: {e}")
        return False


def load_base_graph_cache() -> Optional[nx.DiGraph]:
    """Carrega base_graph de cache."""
    if not CACHE_BASE_GRAPH_FILE.exists():
        return None
    try:
        with open(CACHE_BASE_GRAPH_FILE, "rb") as f:
            base_graph = pickle.load(f)
        print(f"[CACHE] Base graph carregado do cache ({len(base_graph.nodes)} nós, {len(base_graph.edges)} arestas)")
        return base_graph
    except Exception as e:
        print(f"[!] Falha ao carregar base_graph cache: {e}")
        return None


def get_data_hash() -> str:
    """Gera hash dos arquivos de dados (CSVs, GTFS) para validar cache."""
    hash_obj = hashlib.md5()
    data_dir = Path(__file__).parent.parent / "data"
    
    if not data_dir.exists():
        return "no_data_dir"
    
    # Hash CSVs + GTFS
    for pattern in ["*.csv", "bus_gtfs/*"]:
        for file in sorted(data_dir.glob(pattern)):
            if file.is_file():
                try:
                    with open(file, "rb") as f:
                        hash_obj.update(f.read()[:10000])
                except:
                    pass
    return hash_obj.hexdigest()[:16]


def save_multimodal_graph_cache(graph: nx.MultiDiGraph, speed_data: Dict) -> bool:
    """Salva grafo multimodal processado em cache com hash de validação."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        data_hash = get_data_hash()
        with open(CACHE_MULTIMODAL_GRAPH_FILE, "wb") as f:
            pickle.dump({"graph": graph, "speed_data": speed_data}, f)
        with open(CACHE_META_FILE, "w") as f:
            f.write(data_hash)
        print(f"[CACHE] Grafo multimodal salvo (hash={data_hash})")
        return True
    except Exception as e:
        print(f"[!] Falha ao cachear grafo multimodal: {e}")
        return False


def load_multimodal_graph_cache() -> Optional[Tuple[nx.MultiDiGraph, Dict]]:
    """Carrega grafo multimodal de cache se válido."""
    if not CACHE_MULTIMODAL_GRAPH_FILE.exists() or not CACHE_META_FILE.exists():
        return None
    
    try:
        with open(CACHE_META_FILE, "r") as f:
            cached_hash = f.read().strip()
        current_hash = get_data_hash()
        
        if cached_hash != current_hash:
            print(f"[!] Cache inválido (dados mudaram)")
            return None
        
        with open(CACHE_MULTIMODAL_GRAPH_FILE, "rb") as f:
            data = pickle.load(f)
        print(f"[CACHE] Grafo multimodal carregado de cache (hash={cached_hash})")
        return data["graph"], data["speed_data"]
    except Exception as e:
        print(f"[!] Falha ao carregar cache multimodal: {e}")
        return None
