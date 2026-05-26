# ARQUITETURA DO SISTEMA

## Fluxo de Execução

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
│  (Orquestrador do Sistema)                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  Loaders     │  │  Graph       │  │  Routing     │
  │              │  │              │  │              │
  │ • csv_loader │  │ • builder    │  │ • astar      │
  │ • weather_api│  │ • risk_calc  │  │ • path_recon │
  └──────────────┘  │ • cost_calc  │  └──────────────┘
                    │ • normalizer │
                    └──────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                       ┌──────▼──────┐
                       │ input.json  │
                       └─────────────┘
```

## Estrutura de Pastas

```
complexidade/
│
├── data/                          # Dados de entrada (CSVs)
│   ├── crime_rate.csv
│   ├── accident_rate.csv
│   ├── fuel_consumption.csv
│   ├── uber_price_ranges.csv
│   ├── transport_speed.csv
│   ├── flood_risk_streets.csv
│   ├── weather_factors.csv
│   └── tide_factors.csv
│
├── loaders/                       # [1] Carregamento de Dados
│   ├── __init__.py
│   ├── csv_loader.py              # Lê CSVs em DataFrames pandas
│   └── weather_api.py             # Consulta Open-Meteo API
│
├── graph/                         # [2-4] Construção do Grafo
│   ├── __init__.py
│   ├── graph_builder.py           # OSMnx para carregar ruas
│   ├── risk_calculator.py         # Calcula risco por modal
│   ├── cost_calculator.py         # Calcula custo por modal
│   └── normalizer.py              # Normalização Min-Max
│
├── routing/                       # [5-6] Algoritmo de Roteamento
│   ├── __init__.py
│   ├── astar_multimodal.py        # Implementação do A*
│   └── path_reconstructor.py      # Reconstrói rota com detalhes
│
├── main.py                        # Orquestrador (12 etapas)
├── input.json                     # Entrada (origem/destino)
├── output.json                    # Saída (rota calculada)
│
├── requirements.txt               # Dependências Python
├── README.md                      # Documentação completa
└── QUICKSTART.md                  # Guia rápido (este arquivo)
```

## 12 Etapas de Execução

```
[1] CARREGA ENTRADA (input.json)
    └─→ Lê origem, destino, modo_inicial
         ↓
[2] CARREGA CSVs (data/)
    └─→ Via CSVLoader
         ↓
[3] CALCULA RISCOS
    └─→ RiskCalculator (crime + acidentes)
         ↓
[4] CARREGA VELOCIDADES E CUSTOS
    └─→ CostCalculator (fuel, uber, etc)
         ↓
[5] OBTÉM CLIMA (API)
    └─→ WeatherAPI (Open-Meteo) → rain_factor, tide_factor
         ↓
[6] CONSTRÓI GRAFO (OSMnx)
    └─→ GraphBuilder (Recife, Brazil)
         ↓
[7] LOCALIZA NÓS (origem/destino)
    └─→ Encontra nó mais próximo de cada ponto
         ↓
[8] NORMALIZA MÉTRICAS
    └─→ Normalizer (Min-Max para tempo, custo, risco)
         ↓
[9] EXECUTA A*
    └─→ AStarMultimodal (busca ótima multiobjetiva)
         ↓
[10] RECONSTRÓI ROTA
    └─→ PathReconstructor (extrai detalhes de cada segmento)
         ↓
[11] GERA SAÍDA (output.json)
    └─→ JSON com rota e resumo
         ↓
[12] EXIBE RESULTADOS
    └─→ Terminal + output.json
```

## Estados e Transições (A*)

### Estado:
```python
estado = (node_id, modal_atual)
→ (123456, "walk")  # Nó 123456 usando walk
→ (234567, "bus")   # Nó 234567 usando bus
```

### Transições Permitidas:
```
walk  → walk, bus, uber
bike  → bike (sem troca)
car   → car   (sem troca)
moto  → moto  (sem troca)
bus   → bus, walk (descer na parada)
uber  → uber  (sem troca)
```

## Grafo Multimodal

### Estrutura:
```
NetworkX MultiDiGraph com:
- Nós: Interseções de ruas (lat/lon)
- Arestas: 5 cópias por rua (walk, bike, car, moto, uber)
  └─ cada uma com: distancia, tempo, custo, risco, peso
```

### Exemplo:
```
Nó A  ─[walk]──→  Nó B
│     ─[bike]──→   │
│     ─[car]───→   │
│     ─[moto]──→   │
│     ─[uber]──→   │
└─────────────────┘
```

## Función Objetivo (Peso da Aresta)

```python
peso = 0.5 * tempo_normalizado +
       0.3 * custo_normalizado +
       0.2 * risco_normalizado

# Normalização:
tempo_norm = (tempo - tempo_min) / (tempo_max - tempo_min)
custo_norm = (custo - custo_min) / (custo_max - custo_min)
risco_norm = (risco - risco_min) / (risco_max - risco_min)
```

## Integração de Dados Climáticos

```
┌─────────────────┐
│ Open-Meteo API  │
├─────────────────┤
│ precipitation   │
│ rain            │
└─────────────────┘
        │
        ▼
┌─────────────────────────┐
│ WeatherAPI.get_weather  │
│                         │
│ Mapeia precipitação:    │
│ 0mm     → factor 1.0    │
│ <2.5mm  → factor 1.2    │
│ <10mm   → factor 1.5    │
│ <50mm   → factor 2.0    │
│ >50mm   → factor 2.5    │
└─────────────────────────┘
        │
        ▼
tempo_final = tempo_base × rain_factor × tide_factor
```

## Diagrama de Classes

```
┌──────────────────────────┐
│ CSVLoader                │
├──────────────────────────┤
│ + data: Dict[DataFrame]  │
│ + load_all()            │
│ + get(key)              │
└──────────────────────────┘

┌──────────────────────────┐
│ WeatherAPI               │
├──────────────────────────┤
│ + get_weather(lat, lon) │
│ + get_tide_factor()     │
└──────────────────────────┘

┌──────────────────────────┐  ┌──────────────────────────┐
│ GraphBuilder             │→ │ RiskCalculator           │
├──────────────────────────┤  ├──────────────────────────┤
│ + load_base_graph()      │  │ + risk_profiles: Dict    │
│ + build_multimodal_graph │  │ + get_risk(modal)        │
│ + get_speed()            │  │ + get_all_risks()        │
│ + haversine()            │  └──────────────────────────┘
└──────────────────────────┘
        │
        ├──→ ┌──────────────────────────┐
        │    │ CostCalculator           │
        │    ├──────────────────────────┤
        │    │ + calculate_cost()       │
        │    │ + get_all_costs()        │
        │    └──────────────────────────┘
        │
        └──→ ┌──────────────────────────┐
             │ Normalizer               │
             ├──────────────────────────┤
             │ + register_values()      │
             │ + normalize()            │
             │ + normalize_value()      │
             └──────────────────────────┘

┌──────────────────────────┐
│ AStarMultimodal          │
├──────────────────────────┤
│ + heuristic()            │
│ + get_edge_cost()        │
│ + search()               │
│ + _reconstruct_path()    │
└──────────────────────────┘
         │
         └──→ ┌──────────────────────────┐
              │ PathReconstructor        │
              ├──────────────────────────┤
              │ + reconstruct_route()    │
              │ + _build_segment()       │
              └──────────────────────────┘
```

## Fluxo de Dados

```
input.json
    │
    ▼
┌─────────────────┐
│ CSVLoader       │ ──→ crime_rate.csv
│ WeatherAPI      │ ──→ Open-Meteo
└─────────────────┘
    │
    ├─→ RiskCalculator ──→ risk_profiles
    ├─→ CostCalculator ──→ cost_matrix
    ├─→ Normalizer     ──→ norm_params
    │
    ▼
┌─────────────────┐
│ GraphBuilder    │ ──→ multimodal_graph
│ (OSMnx)         │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ AStarMultimodal │ ──→ path: List[(node, modal)]
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ PathRecon-      │ ──→ rota_segments
│ structor        │ ──→ resumo
└─────────────────┘
    │
    ▼
output.json
```

---

**Para mais detalhes, veja README.md**
