# Arquitetura

## Visão Geral

```
┌──────────────────────────────────────────────┐
│ apps/web   (React + Vite + Leaflet)          │
│   ↓ HTTP                                     │
│ apps/api   (FastAPI)                         │
│   ↓ import in-process                        │
│ apps/engine.core.pipeline.run_route()        │
│   ↓                                          │
│   loaders/ → graph/ → routing/ → result      │
└──────────────────────────────────────────────┘
```

Monorepo gerenciado por **Turborepo** (`turbo.json` + workspaces npm).

Três entrypoints, **um único motor** (`apps/engine`):

- **CLI** — `apps/engine/main.py` (lê `input.json`, grava `output/output.json`).
- **API HTTP** — `apps/api/app/main.py` importa `run_route` direto.
- **Front** — `apps/web/src/App.jsx` consome a API.

---

## Engine (`apps/engine/`)

### Camadas

```
main.py            # CLI fino
core/
├── config.py       # constantes + paths absolutos
├── restrictions.py # parse de restricao_modal -> ModalRestriction
├── normalization.py# Min-Max amostrando arestas
└── pipeline.py     # run_route(input_data) -> result_dict  (pura, sem I/O)
graph/              # OSMnx + custos + riscos
routing/            # Dijkstra / A* / reconstrução
loaders/            # CSV + Open-Meteo
scripts/            # utilitários
```

### Pipeline (`run_route`)

1. **Parse de input** — origem, destino, modal inicial, algoritmo, restrição.
2. **Carga de CSVs** — `loaders.csv_loader.CSVLoader(DATA_DIR)`.
3. **Risco por modal** — `graph.risk_calculator.RiskCalculator` combina crime (50%) + acidente (50%).
4. **Custos e velocidades** — `graph.cost_calculator.CostCalculator` (walk=0, bike, bus tarifa R$4.50, carro/moto via combustível R$7.50/L, Uber via fórmula dinâmica).
5. **Clima** — `loaders.weather_api.WeatherAPI` (Open-Meteo) retorna `rain_factor` e `tide_factor`.
6. **Grafo multimodal** — `graph.graph_builder.GraphBuilder` baixa via OSMnx ("Recife, Brazil"), replica arestas por modal e integra GTFS. Cache em `apps/engine/cache/`.
7. **Localização dos nós** — nó mais próximo de origem/destino.
8. **Normalização Min-Max** — `core.normalization.calibrate` amostra até 80k arestas.
9. **Busca** — `DijkstraMultimodal` ou `AStarMultimodal`.
10. **Reconstrução** — `routing.path_reconstructor.PathReconstructor` agrupa por modal.
11. **Saída** — dicionário com `edges`, `segments`, `resumo`. **Sem I/O** — quem chamou decide onde gravar.

### Paths absolutos

`core.config` expõe `ENGINE_ROOT`, `DATA_DIR`, `GTFS_DIR`, `CACHE_DIR`, `OUTPUT_DIR`, `INPUT_FILE`, `OUTPUT_FILE`. O motor funciona independente do CWD — crítico porque o backend executa de `apps/api/`.

---

## Estado de Busca

```python
estado = (node_id, modal_atual, used_bus)
```

`used_bus` permite validar cenários que **exigem** uso de ônibus (`restricao_modal = bus_com_acesso`).

### Transições de Modal

Iniciando em `walk`, o motor permite embarcar em `bus`, `uber_car`, `uber_moto` ou `bike`, e descer para `walk` no final. Modais "próprios" (`car`, `moto`) não são alternados com `walk`.

---

## Grafo Multimodal

`NetworkX MultiDiGraph`:

- **Nós:** interseções OSMnx + paradas GTFS.
- **Arestas:** cada rua replicada por modal motorizado/pedestre; arestas de `bus` adicionadas a partir do GTFS.

Atributos: `modal`, `distance_km`, `maxspeed`, e dados de GTFS (`line`, `gtfs_shape_id`, `source=gtfs`) quando aplicável.

---

## Função Objetivo

```python
tempo_base  = distancia_km / velocidade_kmh
tempo_final = tempo_base * rain_factor * tide_factor

custo       = CostCalculator.calculate_routing_cost(modal, dist, tempo, ...)

risco_base  = RiskCalculator.get_adjusted_risk(modal, climate_factor)
risco       = risco_base * distancia_km / 10

peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
```

Pesos em `core.config.WEIGHTS`.

---

## Integração de Clima

`WeatherAPI` mapeia precipitação → `rain_factor`:

| Precipitação | Fator |
|--------------|-------|
| 0            | 1.0   |
| < 2.5 mm     | 1.2   |
| < 10 mm      | 1.5   |
| < 50 mm      | 2.0   |
| ≥ 50 mm      | 2.5   |

`tide_factor` é heurística baseada em horário. Ambos multiplicam o tempo e ajustam o risco.

---

## Cache do Grafo

`apps/engine/cache/` guarda o grafo OSMnx serializado + dados de velocidade, com hash dos arquivos de `data/`. Primeira execução demora minutos; as seguintes carregam em segundos.

Quando o backend roda como serviço (uvicorn), o grafo vive na memória do worker entre requisições.

---

## API (`apps/api/`)

FastAPI fino que importa `core.pipeline.run_route` in-process:

```python
from core.pipeline import run_route, RouteError
result = run_route(input_dict)
```

Endpoints:

| Rota | Descrição |
|------|-----------|
| `GET /api/health` | Status + caminhos do engine |
| `GET /api/route` | Lê `output/output.json` |
| `POST /api/calculate` | Recalcula e grava `output/output.json` |
| `POST /api/options` | Executa 9 cenários e devolve ranking |

---

## Diagrama de Classes

```
CSVLoader        → DataFrames pandas
WeatherAPI       → rain_factor, tide_factor

GraphBuilder ────┬─→ RiskCalculator
                 ├─→ CostCalculator
                 └─→ Normalizer

DijkstraMultimodal ┐
AStarMultimodal    ├─→ PathReconstructor
                   ┘
```
