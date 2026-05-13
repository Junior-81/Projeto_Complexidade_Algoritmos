#!/usr/bin/env python3
"""Interface simples para visualizar output.json em mapa Folium."""

import json
from pathlib import Path

import folium


MODAL_COLORS = {
    "walk": "green",
    "bike": "blue",
    "car": "gray",
    "moto": "yellow",
    "bus": "red",
    "uber": "black",
    "uber_car": "black",
    "uber_moto": "black",
}


def _build_segments_html(segments: list) -> str:
    if not segments:
        return "<i>Sem segmentos disponiveis.</i>"

    cards = []
    for idx, seg in enumerate(segments, 1):
        modo = seg.get("modo", "walk")
        meio = seg.get("meio", modo)
        color = MODAL_COLORS.get(modo, "black")

        cards.append(
            f"""
            <div style="border-left: 6px solid {color}; background: #f8f9fb;
                        margin: 8px 0; padding: 8px 10px; border-radius: 6px;">
              <b>{idx}. {meio}</b><br>
              Distancia: {seg.get('distancia', 0)} km<br>
              Tempo: {seg.get('tempo', 0)} h<br>
              Custo: R$ {seg.get('custo', 0)}<br>
              Risco: {seg.get('risco_medio', seg.get('risco', 0))}<br>
              Velocidade media: {seg.get('velocidade_media_kmh', 0)} km/h
            </div>
            """
        )

    return "".join(cards)


def load_output(file_path: str = "output.json") -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_center(edges: list) -> list:
    if not edges:
        return [-8.0476, -34.8770]
    first_origin = edges[0].get("origem", [-8.0476, -34.8770])
    return first_origin


def build_map(data: dict) -> folium.Map:
    edges = data.get("edges", [])
    segments = data.get("segments", [])
    resumo = data.get("resumo", {})

    m = folium.Map(location=_get_center(edges), zoom_start=13, control_scale=True)

    for edge in edges:
        origem = edge.get("origem")
        destino = edge.get("destino")
        modo = edge.get("modo", "walk")

        if not origem or not destino:
            continue

        color = MODAL_COLORS.get(modo, "black")
        popup = (
            f"Modo: {modo}<br>"
            f"Distancia: {edge.get('distancia', 0)} km<br>"
            f"Tempo: {edge.get('tempo', 0)} h<br>"
            f"Custo: R$ {edge.get('custo', 0)}<br>"
            f"Risco: {edge.get('risco', 0)}"
        )

        folium.PolyLine(
            locations=[origem, destino],
            color=color,
            weight=4,
            opacity=0.85,
            popup=folium.Popup(popup, max_width=280),
        ).add_to(m)

    resumo_html = f"""
    <div style="position: fixed; bottom: 20px; left: 20px; width: 290px;
                background: white; border: 2px solid #333; border-radius: 8px;
                z-index: 9999; padding: 10px; font-family: Arial, sans-serif; font-size: 13px;">
      <b>Resumo da Rota</b><br>
      Tempo total: {resumo.get('tempo_total', 0)} h<br>
      Custo total: R$ {resumo.get('custo_total', 0)}<br>
      Distancia total: {resumo.get('distancia_total', 0)} km<br>
      Risco medio: {resumo.get('risco_medio', 0)}<br>
      Velocidade media: {resumo.get('velocidade_media_total', 0)} km/h
    </div>
    """

    percurso_html = f"""
    <div style="position: fixed; top: 20px; right: 20px; width: 360px; max-height: 70vh;
                overflow-y: auto; background: white; border: 2px solid #333; border-radius: 8px;
                z-index: 9999; padding: 10px; font-family: Arial, sans-serif; font-size: 13px;">
      <b>Sequencia do Percurso</b><br>
      {_build_segments_html(segments)}
    </div>
    """

    m.get_root().html.add_child(folium.Element(resumo_html))
    m.get_root().html.add_child(folium.Element(percurso_html))
    return m


def main():
    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "output" / "output.json"
    map_path = project_root / "output" / "route_map.html"

    if not output_path.exists():
        raise FileNotFoundError(f"{output_path} nao encontrado. Execute main.py antes.")

    data = load_output(str(output_path))
    route_map = build_map(data)
    map_path.parent.mkdir(exist_ok=True)
    route_map.save(str(map_path))
    print(f"Mapa salvo em {map_path}")


if __name__ == "__main__":
    main()
