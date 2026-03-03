"""
Projeto Acadêmico: Otimização de Rotas Multimodais - Recife
Algoritmos: Dijkstra e A* (A-Estrela)
"""

import heapq
import math
from typing import Dict, List, Tuple, Optional

COORDENADAS: Dict[str, Tuple[float, float]] = {
    'Conde da Boa Vista': (0.0, 0.0),
    'Joana Bezerra': (2.5, 1.0),
    'Shopping': (4.0, 3.5),
    'Padre Carapuceiro': (6.0, 5.5)
}

DADOS_SEGURANCA = {
    'Onibus': {'assaltos': 229, 'mortos': 0, 'acidentes': 221},
    'Carro': {'assaltos': 3651, 'mortos': 9, 'acidentes': 2592},
    'Moto': {'assaltos': 0, 'mortos': 43, 'acidentes': 4234},
    'Bicicleta': {'assaltos': 21, 'mortos': 5, 'acidentes': 135},
    'A pé': {'assaltos': 10345, 'mortos': 43, 'acidentes': 215}
}

DADOS_CUSTO = {
    'Onibus': {'tipo': 'fixo', 'valor': 4.50},
    'Carro': {'tipo': 'por_km', 'km_l': 12.5, 'custo_combustivel': 5.50},
    'Moto': {'tipo': 'por_km', 'km_l': 30, 'custo_combustivel': 5.50},
    'Bicicleta': {'tipo': 'fixo', 'valor': 7.00}
}

def calcular_indice_seguranca(modal: str) -> float:
    dados = DADOS_SEGURANCA.get(modal, {'assaltos': 0, 'mortos': 0, 'acidentes': 0})
    
    peso_assalto = 1.0
    peso_morte = 10.0
    peso_acidente = 0.5
    
    score_perigo = (dados['assaltos'] * peso_assalto + 
                   dados['mortos'] * peso_morte + 
                   dados['acidentes'] * peso_acidente)
    
    if modal == 'Metrô':
        return 1.0
    
    max_score = 15000
    indice_normalizado = max(0, 10 - (score_perigo / max_score) * 10)
    
    return indice_normalizado

def calcular_custo_real(modal: str, distancia_km: float) -> float:
    if modal == 'Metrô':
        return 3.70
    
    if modal == 'A pé':
        return 0.0
    
    dados = DADOS_CUSTO.get(modal)
    if not dados:
        return 15.0
    
    if dados['tipo'] == 'fixo':
        return dados['valor']
    else:
        custo_por_km = dados['custo_combustivel'] / dados['km_l']
        return distancia_km * custo_por_km

def calcular_distancia(origem: str, destino: str) -> float:
    x1, y1 = COORDENADAS[origem]
    x2, y2 = COORDENADAS[destino]
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def criar_grafo() -> Dict[str, List[Tuple[str, str, float, float]]]:
    grafo: Dict[str, List[Tuple[str, str, float, float]]] = {
        'Conde da Boa Vista': [],
        'Joana Bezerra': [],
        'Shopping': [],
        'Padre Carapuceiro': []
    }
    
    conexoes = [
        ('Conde da Boa Vista', 'Joana Bezerra', {
            'Onibus': 15.0, 'Metrô': 8.0, 'A pé': 35.0, 
            'Carro': 10.0, 'Moto': 7.0
        }),
        ('Conde da Boa Vista', 'Shopping', {
            'Onibus': 30.0, 'Carro': 18.0, 'Moto': 13.0
        }),
        ('Joana Bezerra', 'Shopping', {
            'Onibus': 18.0, 'Metrô': 10.0, 'A pé': 40.0,
            'Carro': 12.0, 'Moto': 8.0
        }),
        ('Joana Bezerra', 'Padre Carapuceiro', {
            'Onibus': 35.0, 'Carro': 22.0
        }),
        ('Shopping', 'Padre Carapuceiro', {
            'Onibus': 20.0, 'Metrô': 12.0, 'A pé': 45.0,
            'Carro': 15.0, 'Moto': 10.0
        })
    ]
    
    for origem, destino, modais in conexoes:
        dist_km = calcular_distancia(origem, destino)
        for modal, tempo in modais.items():
            custo = calcular_custo_real(modal, dist_km)
            grafo[origem].append((destino, modal, tempo, custo))
    
    return grafo

def modal_exposto_clima(modal: str) -> bool:
    return modal in ['A pé', 'Moto', 'Bicicleta']

def calcular_peso(tempo: float, custo: float, modal: str, chovendo: bool) -> float:
    seguranca = calcular_indice_seguranca(modal)
    fator_seguranca = (10 - seguranca)
    
    peso_tempo = 0.4
    peso_custo = 0.3
    peso_seguranca = 0.3
    
    peso_base = (tempo * peso_tempo) + (custo * peso_custo) + (fator_seguranca * peso_seguranca)
    
    if chovendo and modal_exposto_clima(modal):
        peso_base += 50.0
    
    return peso_base


def dijkstra(grafo: Dict[str, List[Tuple[str, str, float, float]]], 
             origem: str, destino: str, chovendo: bool) -> Tuple[float, List[Tuple[str, str, float, float]]]:
    distancias: Dict[str, float] = {no: float('inf') for no in grafo.keys()}
    distancias[origem] = 0.0
    
    predecessores: Dict[str, Optional[Tuple[str, str, float, float]]] = {no: None for no in grafo.keys()}
    
    fila_prioridade: List[Tuple[float, str]] = [(0.0, origem)]
    visitados = set()
    
    while fila_prioridade:
        distancia_atual, no_atual = heapq.heappop(fila_prioridade)
        
        if no_atual in visitados:
            continue
            
        visitados.add(no_atual)
        
        if no_atual == destino:
            break
        
        for vizinho, modal, tempo, custo in grafo[no_atual]:
            if vizinho in visitados:
                continue
            
            peso_aresta = calcular_peso(tempo, custo, modal, chovendo)
            nova_distancia = distancia_atual + peso_aresta
            
            if nova_distancia < distancias[vizinho]:
                distancias[vizinho] = nova_distancia
                predecessores[vizinho] = (no_atual, modal, tempo, custo)
                heapq.heappush(fila_prioridade, (nova_distancia, vizinho))
    
    caminho: List[Tuple[str, str, float, float]] = []
    no_atual = destino
    
    while predecessores[no_atual] is not None:
        no_anterior, modal_usado, tempo, custo = predecessores[no_atual]
        caminho.append((no_atual, modal_usado, tempo, custo))
        no_atual = no_anterior
    
    caminho.append((origem, 'Inicio', 0.0, 0.0))
    caminho.reverse()
    
    return distancias[destino], caminho


def calcular_heuristica(no_atual: str, no_destino: str) -> float:
    x1, y1 = COORDENADAS[no_atual]
    x2, y2 = COORDENADAS[no_destino]
    
    distancia_euclidiana = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    tempo_estimado = distancia_euclidiana / 1.0
    heuristica = tempo_estimado * 0.4
    
    return heuristica

def a_estrela(grafo: Dict[str, List[Tuple[str, str, float, float]]], 
              origem: str, destino: str, chovendo: bool) -> Tuple[float, List[Tuple[str, str, float, float]]]:
    g_score: Dict[str, float] = {no: float('inf') for no in grafo.keys()}
    g_score[origem] = 0.0
    
    f_score: Dict[str, float] = {no: float('inf') for no in grafo.keys()}
    f_score[origem] = calcular_heuristica(origem, destino)
    
    predecessores: Dict[str, Optional[Tuple[str, str, float, float]]] = {no: None for no in grafo.keys()}
    
    fila_prioridade: List[Tuple[float, str]] = [(f_score[origem], origem)]
    visitados = set()
    
    while fila_prioridade:
        _, no_atual = heapq.heappop(fila_prioridade)
        
        if no_atual in visitados:
            continue
        
        visitados.add(no_atual)
        
        if no_atual == destino:
            break
        
        for vizinho, modal, tempo, custo in grafo[no_atual]:
            if vizinho in visitados:
                continue
            
            peso_aresta = calcular_peso(tempo, custo, modal, chovendo)
            g_tentativo = g_score[no_atual] + peso_aresta
            
            if g_tentativo < g_score[vizinho]:
                predecessores[vizinho] = (no_atual, modal, tempo, custo)
                g_score[vizinho] = g_tentativo
                h_vizinho = calcular_heuristica(vizinho, destino)
                f_score[vizinho] = g_tentativo + h_vizinho
                heapq.heappush(fila_prioridade, (f_score[vizinho], vizinho))
    
    caminho: List[Tuple[str, str, float, float]] = []
    no_atual = destino
    
    while predecessores[no_atual] is not None:
        no_anterior, modal_usado, tempo, custo = predecessores[no_atual]
        caminho.append((no_atual, modal_usado, tempo, custo))
        no_atual = no_anterior
    
    caminho.append((origem, 'Inicio', 0.0, 0.0))
    caminho.reverse()
    
    return g_score[destino], caminho


def imprimir_resultado(algoritmo: str, custo_total: float, 
                      caminho: List[Tuple[str, str, float, float]], chovendo: bool) -> None:
    print(f"\n{'='*80}")
    print(f"ALGORITMO: {algoritmo}")
    print(f"Condicao Climatica: {'CHUVA' if chovendo else 'SOL'}")
    print(f"{'='*80}")
    print(f"Custo Total (ponderado): {custo_total:.2f}")
    print(f"\nRota Detalhada:")
    print(f"{'-'*80}")
    
    tempo_total = 0.0
    custo_monetario_total = 0.0
    
    for i, (no, modal, tempo, custo) in enumerate(caminho):
        if i == 0:
            print(f"  {i+1}. ORIGEM: {no}")
        else:
            tempo_total += tempo
            custo_monetario_total += custo
            seguranca = calcular_indice_seguranca(modal)
            print(f"  {i+1}. {modal:15s} -> {no:25s} | Tempo: {tempo:5.1f}min | Custo: R${custo:5.2f} | Seguranca: {seguranca:.1f}/10")
    
    print(f"{'-'*80}")
    print(f"Tempo Total: {tempo_total:.1f} minutos")
    print(f"Custo Monetario Total: R$ {custo_monetario_total:.2f}")
    print(f"{'='*80}\n")

def analisar_melhor_opcao(caminho: List[Tuple[str, str, float, float]], chovendo: bool) -> Dict:
    if len(caminho) <= 1:
        return {}
    
    modais_usados = [modal for _, modal, _, _ in caminho[1:]]
    tempo_total = sum(tempo for _, _, tempo, _ in caminho[1:])
    custo_total = sum(custo for _, _, _, custo in caminho[1:])
    
    segurancas = [calcular_indice_seguranca(modal) for modal in modais_usados]
    seguranca_media = sum(segurancas) / len(segurancas) if segurancas else 0
    
    return {
        'modais': modais_usados,
        'tempo': tempo_total,
        'custo': custo_total,
        'seguranca': seguranca_media,
        'clima': 'Adequado' if not any(modal_exposto_clima(m) for m in modais_usados) or not chovendo else 'Inadequado'
    }

def comparar_algoritmos(grafo: Dict[str, List[Tuple[str, str, float, float]]], 
                       origem: str, destino: str, chovendo: bool) -> None:
    print(f"\n{'#'*80}")
    print(f"# COMPARACAO: {origem} -> {destino}")
    print(f"{'#'*80}")
    
    custo_dijkstra, caminho_dijkstra = dijkstra(grafo, origem, destino, chovendo)
    imprimir_resultado("DIJKSTRA", custo_dijkstra, caminho_dijkstra, chovendo)
    
    custo_a_estrela, caminho_a_estrela = a_estrela(grafo, origem, destino, chovendo)
    imprimir_resultado("A* (A-ESTRELA)", custo_a_estrela, caminho_a_estrela, chovendo)
    
    analise = analisar_melhor_opcao(caminho_dijkstra, chovendo)
    
    print(f"{'='*80}")
    print(f"ANALISE DA MELHOR ROTA:")
    print(f"{'-'*80}")
    if analise:
        print(f"Modais utilizados: {' -> '.join(analise['modais'])}")
        print(f"Tempo total de viagem: {analise['tempo']:.1f} minutos")
        print(f"Custo monetario total: R$ {analise['custo']:.2f}")
        print(f"Seguranca media: {analise['seguranca']:.1f}/10")
        print(f"Adequacao ao clima: {analise['clima']}")
        
        print(f"\nJUSTIFICATIVA:")
        if analise['tempo'] < 30:
            print(f"  - Rota RAPIDA (menos de 30 minutos)")
        if analise['custo'] < 10:
            print(f"  - Rota ECONOMICA (menos de R$ 10)")
        if analise['seguranca'] >= 7:
            print(f"  - Rota SEGURA (indice >= 7/10)")
        elif analise['seguranca'] < 5:
            print(f"  - ATENCAO: Rota com indice de seguranca BAIXO")
        
        if chovendo and analise['clima'] == 'Adequado':
            print(f"  - Rota PROTEGIDA da chuva")
        elif chovendo and analise['clima'] == 'Inadequado':
            print(f"  - ALERTA: Rota exposta a chuva")
    
    print(f"{'='*80}\n")


def imprimir_tabela_dados() -> None:
    print("\n" + "="*80)
    print("DADOS DE SEGURANCA COLETADOS (Recife 2024-2025)")
    print("="*80)
    print(f"{'Modal':<15} {'Assaltos':<12} {'Mortes':<12} {'Acidentes':<12} {'Indice Seg.':<12}")
    print("-"*80)
    
    for modal, dados in DADOS_SEGURANCA.items():
        indice = calcular_indice_seguranca(modal)
        print(f"{modal:<15} {dados['assaltos']:<12} {dados['mortos']:<12} {dados['acidentes']:<12} {indice:<12.2f}/10")
    
    metro_indice = calcular_indice_seguranca('Metrô')
    print(f"{'Metrô':<15} {'N/A':<12} {'N/A':<12} {'N/A':<12} {metro_indice:<12.2f}/10")
    print("="*80)
    
    print("\nDADOS DE CUSTO")
    print("="*80)
    print(f"{'Modal':<15} {'Tipo':<15} {'Detalhe':<40}")
    print("-"*80)
    print(f"{'Onibus':<15} {'Fixo':<15} {'R$ 4.50 por passagem':<40}")
    print(f"{'Metrô':<15} {'Fixo':<15} {'R$ 3.70 por passagem':<40}")
    print(f"{'Carro':<15} {'Por km':<15} {'12.5 km/L * R$ 5.50/L = R$ 0.44/km':<40}")
    print(f"{'Moto':<15} {'Por km':<15} {'30 km/L * R$ 5.50/L = R$ 0.18/km':<40}")
    print(f"{'Bicicleta':<15} {'Fixo':<15} {'R$ 7.00 (aluguel Itau)':<40}")
    print(f"{'A pé':<15} {'Gratuito':<15} {'R$ 0.00':<40}")
    print("="*80 + "\n")

def main() -> None:
    print("\n" + "="*80)
    print(" SISTEMA DE OTIMIZACAO DE ROTAS MULTIMODAIS - RECIFE")
    print(" Algoritmos: Dijkstra vs A* com dados reais de seguranca e custo")
    print("="*80)
    
    imprimir_tabela_dados()
    
    grafo = criar_grafo()
    origem = 'Conde da Boa Vista'
    destino = 'Padre Carapuceiro'
    
    print("\n" + "="*80)
    print("CENARIO 1: DIA ENSOLARADO")
    print("="*80)
    comparar_algoritmos(grafo, origem, destino, chovendo=False)
    
    print("\n" + "="*80)
    print("CENARIO 2: CHUVA FORTE")
    print("="*80)
    comparar_algoritmos(grafo, origem, destino, chovendo=True)
    
    print("\n" + "="*80)
    print("CONCLUSAO DO ESTUDO:")
    print("-"*80)
    print("O sistema considera multiplos fatores baseados em dados reais:")
    print("  - Tempo de deslocamento")
    print("  - Custo financeiro (calculado por km para carro/moto)")
    print("  - Seguranca (baseada em assaltos, mortes e acidentes reais)")
    print("  - Condicoes climaticas (penalidade para modais expostos)")
    print("\nO diferencial cientifico: a uniao desses dados muda completamente")
    print("o trajeto sugerido, indo alem da simples distancia minima.")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
