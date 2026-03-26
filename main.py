#!/usr/bin/env python3
"""
Sistema de Recomendação de Rotas Multimodais.
Suporta Dijkstra e A* com otimizacao multiobjetivo (tempo, custo, risco).
"""

import json
import sys
from pathlib import Path

# Adiciona diretórios ao path
sys.path.insert(0, str(Path(__file__).parent))

from loaders.csv_loader import CSVLoader
from loaders.weather_api import WeatherAPI
from graph.graph_builder import GraphBuilder
from graph.risk_calculator import RiskCalculator
from graph.cost_calculator import CostCalculator
from graph.normalizer import Normalizer
from routing.astar_multimodal import AStarMultimodal
from routing.dijkstra_multimodal import DijkstraMultimodal
from routing.path_reconstructor import PathReconstructor


GASOLINE_PRICE_PER_LITER = 7.50


def load_input() -> dict:
    """Carrega input.json."""
    try:
        with open("input.json", "r") as f:
            data = json.load(f)
        print(f"✓ Input carregado:")
        print(f"  Origem: {data['origem']}")
        print(f"  Destino: {data['destino']}")
        print(f"  Modal inicial: {data['modo_inicial']}")
        return data
    except Exception as e:
        print(f"✗ Erro ao carregar input.json: {e}")
        sys.exit(1)


def find_nearest_node(graph, lat: float, lon: float):
    """Encontra o nó mais próximo no grafo."""
    import osmnx as ox

    try:
        return ox.distance.nearest_nodes(graph, lon, lat)
    except:
        # Fallback: procura manualmente o nó mais próximo
        min_dist = float("inf")
        nearest = None
        for node, data in graph.nodes(data=True):
            node_lat = data.get("y", 0)
            node_lon = data.get("x", 0)
            dist = (node_lat - lat) ** 2 + (node_lon - lon) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = node
        return nearest


def main():
    """Executa o sistema principal."""

    print("\n" + "=" * 60)
    print("SISTEMA DE ROTAS MULTIMODAIS")
    print("=" * 60 + "\n")

    # ETAPA 1: Carrega input
    print("[1] Carregando entrada...")
    input_data = load_input()
    origem_lat, origem_lon = input_data["origem"]
    destino_lat, destino_lon = input_data["destino"]
    modo_inicial = input_data["modo_inicial"].lower()
    algoritmo = input_data.get("algoritmo", "dijkstra").lower()
    if algoritmo not in {"dijkstra", "astar"}:
        print(f"! Algoritmo '{algoritmo}' invalido. Usando dijkstra.")
        algoritmo = "dijkstra"

    # ETAPA 2: Carrega CSVs
    print("\n[2] Carregando CSVs...")
    loader = CSVLoader("data")
    data = loader.load_all()

    # ETAPA 3: Calcula risco por modal
    print("\n[3] Calculando riscos...")
    risk_calc = RiskCalculator(data.get("crime_rate"), data.get("accident_rate"))
    print(f"✓ Riscos calculados:")
    for modal, risk in risk_calc.get_all_risks().items():
        print(f"  {modal}: {risk:.3f}")

    # ETAPA 4: Carrega velocidades e custos
    print("\n[4] Carregando velocidades e custos...")
    cost_calc = CostCalculator(
        data.get("fuel_consumption"),
        data.get("uber_prices"),
        data.get("transport_speed"),
        gas_price=GASOLINE_PRICE_PER_LITER,
    )
    print(f"✓ Custos configurados")

    # ETAPA 5: Obtém clima via API
    print("\n[5] Obtendo condições climáticas...")
    weather_api = WeatherAPI()
    weather = weather_api.get_weather(origem_lat, origem_lon)
    rain_factor = weather.get("rain_factor", 1.0)
    tide_factor = weather_api.get_tide_factor(origem_lat, origem_lon)

    print(f"✓ Clima: {weather.get('precipitation', 0):.1f}mm precipitação")
    print(f"  Fator chuva: {rain_factor:.2f}")
    print(f"  Fator maré: {tide_factor:.2f}")

    # ETAPA 6: Constrói grafo com OSMnx
    print("\n[6] Construindo grafo multimodal...")
    builder = GraphBuilder("Recife, Brazil")
    builder.load_base_graph()
    builder.load_speed_data(data.get("transport_speed"))
    builder.load_flood_data(data.get("flood_risk"))

    graph = builder.build_multimodal_graph()

    # Integra trajetos de ônibus validados por GTFS
    builder.add_gtfs_bus_routes("data/bus_gtfs")

    if graph is None:
        print("✗ Falha ao construir grafo")
        sys.exit(1)

    # ETAPA 7: Encontra nós mais próximos
    print("\n[7] Localizando nós no grafo...")
    start_node = find_nearest_node(builder.base_graph, origem_lat, origem_lon)
    goal_node = find_nearest_node(builder.base_graph, destino_lat, destino_lon)

    print(f"✓ Origem: nó {start_node}")
    print(f"✓ Destino: nó {goal_node}")

    # ETAPA 8: Calcula tempos, custos e riscos das arestas (amostra)
    print("\n[8] Normalizando tempo, custo e risco...")
    normalizer = Normalizer()

    # Amostras valores para normalização
    sample_distances = [0.5, 1.0, 2.0, 5.0, 10.0]
    for dist in sample_distances:
        for modal in ["walk", "bike", "car", "moto", "bus", "uber_car", "uber_moto"]:
            speed = builder.get_speed(modal)
            tempo = (dist / speed) * rain_factor * tide_factor if speed > 0 else 10
            custo = cost_calc.calculate_cost(
                modal,
                dist,
                time_minutes=tempo * 60,
                avg_speed_kmh=speed,
                rain_factor=rain_factor,
            )
            climate_factor = rain_factor * tide_factor
            risco = risk_calc.get_adjusted_risk(modal, climate_factor)
            normalizer.register_values(tempo, custo, risco)

    norm_params = normalizer.normalize()
    print(f"✓ Parâmetros de normalização calculados")
    print(
        f"  Tempo: [{norm_params['time']['min']:.2f}, {norm_params['time']['max']:.2f}]"
    )
    print(
        f"  Custo: [{norm_params['cost']['min']:.2f}, {norm_params['cost']['max']:.2f}]"
    )
    print(
        f"  Risco: [{norm_params['risk']['min']:.2f}, {norm_params['risk']['max']:.2f}]"
    )

    # ETAPA 9: Executa busca multimodal
    print(f"\n[9] Executando {algoritmo.upper()} (busca em grafo multimodal)...")
    astar = AStarMultimodal(graph, norm_params)
    dijkstra = DijkstraMultimodal(graph, norm_params)

    # Define função para obter velocidade
    speed_getter = lambda m: builder.get_speed(m)

    start_state = (start_node, modo_inicial)
    goal_state = (goal_node, modo_inicial)

    if algoritmo == "astar":
        path = astar.search(
            start_state,
            goal_state,
            cost_calc,
            risk_calc,
            rain_factor=rain_factor,
            tide_factor=tide_factor,
            speed_getter=speed_getter,
            start_modal=modo_inicial,
        )
    else:
        path = dijkstra.search(
            start_state,
            goal_state,
            cost_calc,
            risk_calc,
            rain_factor=rain_factor,
            tide_factor=tide_factor,
            speed_getter=speed_getter,
            start_modal=modo_inicial,
        )

    if path is None:
        print("✗ Nenhuma rota encontrada")
        sys.exit(1)

    print(f"✓ Rota encontrada com {len(path)} etapas")

    # ETAPA 10: Reconstrói rota com detalhes
    print("\n[10] Reconstruindo detalhes da rota...")
    reconstructor = PathReconstructor(
        graph,
        cost_calc,
        risk_calc,
        norm_params,
        rain_factor=rain_factor,
        tide_factor=tide_factor,
        speed_data=builder.speed_data,
    )

    result = reconstructor.reconstruct_route(path)

    # ETAPA 11: Gera JSON de saída
    print("\n[11] Gerando saída...")
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✓ Saída salva em output.json")

    # ETAPA 12: Exibe resumo
    print("\n" + "=" * 60)
    print("RESUMO DA ROTA RECOMENDADA")
    print("=" * 60)
    resumo = result["resumo"]
    print(f"Tempo total:      {resumo['tempo_total']} horas")
    print(f"Custo total:      R$ {resumo['custo_total']:.2f}")
    print(f"Distância:        {resumo['distancia_total']:.2f} km")
    print(f"Risco médio:      {resumo['risco_medio']:.3f}")
    print(f"Velocidade média: {resumo['velocidade_media_total']:.2f} km/h")
    print(f"Número de segmentos: {len(result['segments'])}")
    print(f"Número de arestas:   {len(result['edges'])}")
    print("=" * 60 + "\n")

    # Exibe detalhes dos segmentos
    print("DETALHES DOS SEGMENTOS:")
    for i, seg in enumerate(result["segments"], 1):
        meio = seg.get("meio", seg["modo"])
        print(f"\n{i}. {meio.upper()}")
        print(f"   De: {seg['origem']}")
        print(f"   Para: {seg['destino']}")
        print(
            f"   Tempo: {seg['tempo']} h | Distância: {seg['distancia']} km | Custo: R$ {seg['custo']:.2f}"
        )

    print("\n✓ Sistema concluído com sucesso!\n")


if __name__ == "__main__":
    main()
