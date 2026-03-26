import osmnx as ox
import matplotlib.pyplot as plt

# Define o nome da cidade
cidade = "Recife, Pernambuco, Brazil"

# Baixa o grafo da cidade (rede de ruas para carros)
G = ox.graph_from_place(cidade, network_type="drive")

# Plota o grafo
fig, ax = ox.plot_graph(G)
