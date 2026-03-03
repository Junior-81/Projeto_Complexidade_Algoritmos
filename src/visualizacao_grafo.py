"""
Visualizacao do Grafo Multimodal - Recife
Mostra a estrutura da rede de transporte com multiplas arestas entre os mesmos nos
"""

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

COORDENADAS = {
    'Conde da Boa Vista': (0, 10),
    'Joana Bezerra': (8, 8),
    'Shopping': (12, 5),
    'Padre Carapuceiro': (15, 2)
}

DADOS_SEGURANCA = {
    'Onibus': 9.77,
    'Metro': 10.00,
    'Carro': 6.64,
    'Moto': 8.30,
    'Bicicleta': 9.91,
    'A pe': 2.74
}

CORES_MODAIS = {
    'Onibus': '#FF6B6B',
    'Metro': '#4ECDC4',
    'Carro': '#45B7D1',
    'Moto': '#96CEB4',
    'Bicicleta': '#FFEAA7',
    'A pe': '#DFE6E9'
}

def criar_grafo_multimodal():
    G = nx.MultiDiGraph()
    
    for node, pos in COORDENADAS.items():
        G.add_node(node, pos=pos)
    
    conexoes = [
        ('Conde da Boa Vista', 'Joana Bezerra', [
            {'modal': 'Onibus', 'tempo': 15, 'custo': 4.50, 'seg': 9.77},
            {'modal': 'Metro', 'tempo': 8, 'custo': 3.70, 'seg': 10.00},
            {'modal': 'A pe', 'tempo': 35, 'custo': 0.00, 'seg': 2.74},
            {'modal': 'Carro', 'tempo': 10, 'custo': 1.18, 'seg': 6.64},
            {'modal': 'Moto', 'tempo': 7, 'custo': 0.49, 'seg': 8.30}
        ]),
        ('Conde da Boa Vista', 'Shopping', [
            {'modal': 'Onibus', 'tempo': 30, 'custo': 4.50, 'seg': 9.77},
            {'modal': 'Carro', 'tempo': 18, 'custo': 2.38, 'seg': 6.64},
            {'modal': 'Moto', 'tempo': 13, 'custo': 0.97, 'seg': 8.30}
        ]),
        ('Joana Bezerra', 'Shopping', [
            {'modal': 'Onibus', 'tempo': 18, 'custo': 4.50, 'seg': 9.77},
            {'modal': 'Metro', 'tempo': 10, 'custo': 3.70, 'seg': 10.00},
            {'modal': 'A pe', 'tempo': 40, 'custo': 0.00, 'seg': 2.74},
            {'modal': 'Carro', 'tempo': 12, 'custo': 1.56, 'seg': 6.64},
            {'modal': 'Moto', 'tempo': 8, 'custo': 0.64, 'seg': 8.30}
        ]),
        ('Joana Bezerra', 'Padre Carapuceiro', [
            {'modal': 'Onibus', 'tempo': 35, 'custo': 4.50, 'seg': 9.77},
            {'modal': 'Carro', 'tempo': 22, 'custo': 2.51, 'seg': 6.64}
        ]),
        ('Shopping', 'Padre Carapuceiro', [
            {'modal': 'Onibus', 'tempo': 20, 'custo': 4.50, 'seg': 9.77},
            {'modal': 'Metro', 'tempo': 12, 'custo': 3.70, 'seg': 10.00},
            {'modal': 'A pe', 'tempo': 45, 'custo': 0.00, 'seg': 2.74},
            {'modal': 'Carro', 'tempo': 15, 'custo': 1.74, 'seg': 6.64},
            {'modal': 'Moto', 'tempo': 10, 'custo': 0.52, 'seg': 8.30}
        ])
    ]
    
    for origem, destino, modais in conexoes:
        for info in modais:
            G.add_edge(
                origem, 
                destino, 
                key=info['modal'],
                modal=info['modal'],
                tempo=info['tempo'],
                custo=info['custo'],
                seguranca=info['seg'],
                color=CORES_MODAIS.get(info['modal'], '#95A5A6')
            )
    
    return G

def visualizar_grafo_completo(G, filename='output/grafo_completo.png'):
    fig, ax = plt.subplots(figsize=(18, 12))
    pos = nx.get_node_attributes(G, 'pos')
    
    nx.draw_networkx_nodes(G, pos, node_color='#2C3E50', node_size=3000, 
                          alpha=0.9, ax=ax)
    
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold', 
                           font_color='white', ax=ax)
    
    edge_colors = [G[u][v][k]['color'] for u, v, k in G.edges(keys=True)]
    
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, 
                          width=2, alpha=0.6, 
                          connectionstyle='arc3,rad=0.1',
                          arrows=True, arrowsize=15, ax=ax)
    
    legend_elements = [plt.Line2D([0], [0], color=cor, linewidth=4, 
                                  label=f'{modal} (Seg: {DADOS_SEGURANCA[modal]:.1f}/10)')
                      for modal, cor in CORES_MODAIS.items()]
    
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10, 
             title='Modais de Transporte', title_fontsize=12)
    
    ax.set_title('Grafo Multimodal - Rede de Transporte Recife\n(MultiDiGraph com multiplas arestas entre mesmos nos)', 
                fontsize=16, fontweight='bold', pad=20)
    
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Grafo completo salvo em: {filename}")
    plt.close()

def visualizar_melhor_rota(G, rota_sol, rota_chuva, filename='output/melhor_rota_comparacao.png'):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    pos = nx.get_node_attributes(G, 'pos')
    
    for ax, rota_info, titulo in [(ax1, rota_sol, 'DIA ENSOLARADO'), 
                                   (ax2, rota_chuva, 'CHUVA FORTE')]:
        nx.draw_networkx_nodes(G, pos, node_color='#ECF0F1', node_size=2500, 
                              alpha=0.3, ax=ax)
        
        nx.draw_networkx_edges(G, pos, edge_color='#BDC3C7', width=1, 
                              alpha=0.2, connectionstyle='arc3,rad=0.1',
                              arrows=True, arrowsize=10, ax=ax)
        
        caminho = rota_info['caminho']
        for i in range(len(caminho) - 1):
            origem = caminho[i]
            destino = caminho[i + 1]
            modal = rota_info['modais'][i]
            
            edge_data = G.get_edge_data(origem, destino, key=modal)
            if edge_data:
                cor = edge_data['color']
                nx.draw_networkx_edges(G, pos, [(origem, destino)], 
                                      edge_color=cor, width=5, alpha=0.9,
                                      connectionstyle='arc3,rad=0.1',
                                      arrows=True, arrowsize=20, ax=ax)
        
        node_colors = ['#E74C3C' if node == caminho[0] 
                      else '#27AE60' if node == caminho[-1]
                      else '#3498DB' for node in G.nodes()]
        
        highlighted_nodes = [node for node in caminho]
        other_nodes = [node for node in G.nodes() if node not in highlighted_nodes]
        
        if other_nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=other_nodes, 
                                  node_color='#ECF0F1', node_size=2500, 
                                  alpha=0.3, ax=ax)
        
        nx.draw_networkx_nodes(G, pos, nodelist=highlighted_nodes, 
                              node_color=[node_colors[list(G.nodes()).index(n)] 
                                         for n in highlighted_nodes],
                              node_size=3000, alpha=0.9, ax=ax)
        
        nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold', 
                               font_color='white', ax=ax)
        
        info_text = (f"Modal: {' → '.join(rota_info['modais'])}\n"
                    f"Tempo: {rota_info['tempo']:.0f} min\n"
                    f"Custo: R$ {rota_info['custo']:.2f}\n"
                    f"Seguranca: {rota_info['seguranca']:.1f}/10")
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        ax.set_title(titulo, fontsize=14, fontweight='bold', pad=15)
        ax.axis('off')
    
    fig.suptitle('Comparacao: Como o Clima Muda a Rota Otima', 
                fontsize=18, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Comparacao de rotas salva em: {filename}")
    plt.close()

def criar_grafo_metrica_seguranca(filename='output/grafico_seguranca.png'):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    modais = list(DADOS_SEGURANCA.keys())
    scores = list(DADOS_SEGURANCA.values())
    cores = [CORES_MODAIS[m] for m in modais]
    
    bars = ax.barh(modais, scores, color=cores, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    for i, (modal, score) in enumerate(zip(modais, scores)):
        ax.text(score + 0.2, i, f'{score:.2f}', va='center', fontweight='bold', fontsize=11)
    
    ax.axvline(x=7, color='orange', linestyle='--', linewidth=2, label='Limite Seguro (7.0)')
    ax.axvline(x=5, color='red', linestyle='--', linewidth=2, label='Limite Critico (5.0)')
    
    ax.set_xlabel('Indice de Seguranca (0-10)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Modal de Transporte', fontsize=13, fontweight='bold')
    ax.set_title('Indice de Seguranca por Modal\n(Baseado em Assaltos, Mortes e Acidentes - Recife 2024-2025)', 
                fontsize=15, fontweight='bold', pad=20)
    
    ax.set_xlim(0, 11)
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Grafico de seguranca salvo em: {filename}")
    plt.close()

def main():
    print("\n" + "="*80)
    print("GERANDO VISUALIZACOES DO GRAFO MULTIMODAL")
    print("="*80 + "\n")
    
    G = criar_grafo_multimodal()
    
    print(f"Grafo criado com:")
    print(f"  - {G.number_of_nodes()} nos (locais)")
    print(f"  - {G.number_of_edges()} arestas (conexoes multimodais)")
    print(f"  - Tipo: MultiDiGraph (aceita multiplas arestas entre mesmos nos)\n")
    
    visualizar_grafo_completo(G, 'output/grafo_completo.png')
    
    rota_sol = {
        'caminho': ['Conde da Boa Vista', 'Shopping', 'Padre Carapuceiro'],
        'modais': ['Moto', 'Moto'],
        'tempo': 23.0,
        'custo': 1.49,
        'seguranca': 8.3
    }
    
    rota_chuva = {
        'caminho': ['Conde da Boa Vista', 'Joana Bezerra', 'Padre Carapuceiro'],
        'modais': ['Carro', 'Carro'],
        'tempo': 32.0,
        'custo': 3.69,
        'seguranca': 6.6
    }
    
    visualizar_melhor_rota(G, rota_sol, rota_chuva, 'output/melhor_rota_comparacao.png')
    
    criar_grafo_metrica_seguranca('output/grafico_seguranca.png')
    
    print("\n" + "="*80)
    print("VISUALIZACOES GERADAS COM SUCESSO!")
    print("="*80)
    print("\nArquivos criados na pasta 'output/':")
    print("  1. grafo_completo.png - Grafo completo com todos os modais")
    print("  2. melhor_rota_comparacao.png - Comparacao Sol vs Chuva")
    print("  3. grafico_seguranca.png - Indice de seguranca por modal")
    print("\n")

if __name__ == "__main__":
    main()
