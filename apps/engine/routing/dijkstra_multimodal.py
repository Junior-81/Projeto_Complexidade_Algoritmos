"""Dijkstra multimodal: prioridade da fila é o custo acumulado real g(n)."""

from __future__ import annotations

from routing.search_base import MultimodalSearchBase


class DijkstraMultimodal(MultimodalSearchBase):
    """Dijkstra padrão — ótimo garantido para pesos não negativos."""

    name = "Dijkstra"

    # priority() é herdado: retorna g_score, que é exatamente o que Dijkstra precisa.
