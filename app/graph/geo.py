"""Utilitarios geograficos compartilhados pelo grafo e pelos algoritmos.

Reune a distancia de Haversine (usada como peso geometrico das arestas e como
heuristica do A*) e um indice espacial em grade (`SpatialGrid`) que permite
encontrar paradas vizinhas em tempo proximo de O(1) por consulta, sem varrer as
~7.000 paradas a cada vez.
"""

from __future__ import annotations

import math
from collections import defaultdict

# No do grafo: tupla (latitude, longitude).
No = tuple[float, float]

# Raio medio da Terra em km (usado na formula de Haversine).
_EARTH_RADIUS_KM = 6371.0088


def haversine_km(origem: No, destino: No) -> float:
    """Distancia do grande circulo entre dois pontos (lat, lon) em km.

    Formula de Haversine. Como e a menor distancia possivel entre dois pontos
    sobre a esfera, serve de heuristica *admissivel* para o A* (nunca superestima
    o trajeto real, que so pode ser mais longo).
    """
    lat1, lon1 = origem
    lat2, lon2 = destino
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class SpatialGrid:
    """Indice espacial simples baseado em grade de celulas.

    Cada no e jogado numa celula de lado ~`cell_size_deg` graus. A busca por
    vizinhos olha apenas a celula do ponto e as 8 adjacentes, tornando a
    construcao do grafo de proximidade quase linear no numero de paradas.
    """

    def __init__(self, cell_size_deg: float) -> None:
        self.cell_size = cell_size_deg
        self._cells: dict[tuple[int, int], list[No]] = defaultdict(list)

    def _cell_of(self, no: No) -> tuple[int, int]:
        lat, lon = no
        return (int(lat / self.cell_size), int(lon / self.cell_size))

    def add(self, no: No) -> None:
        self._cells[self._cell_of(no)].append(no)

    def candidates(self, no: No) -> list[No]:
        """Nos nas 9 celulas ao redor de `no` (incluindo a propria)."""
        ci, cj = self._cell_of(no)
        out: list[No] = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                out.extend(self._cells.get((ci + di, cj + dj), ()))
        return out

    def nearest(self, no: No) -> No | None:
        """Retorna o no cadastrado mais proximo de `no` (ou None se vazio)."""
        best: No | None = None
        best_dist = math.inf
        candidates = self.candidates(no)
        # Se nenhuma celula vizinha tem pontos, cai no escaneamento global.
        pool = candidates if candidates else [
            p for bucket in self._cells.values() for p in bucket
        ]
        for cand in pool:
            d = haversine_km(no, cand)
            if d < best_dist:
                best_dist, best = d, cand
        return best
