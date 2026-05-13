# Dados Externos

O motor depende de três fontes: **CSVs locais** (`apps/engine/data/*.csv`), **GTFS de ônibus** (`apps/engine/data/bus_gtfs/`) e a **API Open-Meteo**. A pasta `apps/engine/data/` **não está versionada** (vide `.gitignore`); cada um precisa colocá-la localmente.

Existem fallbacks no código para a maioria dos arquivos ausentes — o sistema continua funcionando, mas o resultado fica menos realista.

---

## CSVs (`apps/engine/data/*.csv`)

Carregados por [loaders/csv_loader.py](../apps/engine/loaders/csv_loader.py).

| Arquivo | Conteúdo | Usado por |
|---------|----------|-----------|
| `crime_rate.csv` | Risco de assalto por modal | `RiskCalculator` |
| `accident_rate.csv` | Risco de acidente (deaths/involved) por modal | `RiskCalculator` |
| `fuel_consumption.csv` | Consumo (L/km ou km/L) por modal motorizado | `CostCalculator` |
| `uber_price_ranges.csv` | Faixas de tarifa Uber (base, valor/km, valor/min) | `CostCalculator` |
| `transport_speed.csv` | Velocidade média por modal (km/h) | `GraphBuilder`, `CostCalculator` |
| `flood_risk_streets.csv` | Multiplicador de alagamento por rua | `GraphBuilder` |
| `weather_factors.csv` | Reservado para extensão | — |
| `tide_factors.csv` | Reservado para extensão | — |

---

## GTFS (`apps/engine/data/bus_gtfs/`)

Lido por `GraphBuilder.add_gtfs_bus_routes()`. Arquivos esperados:

- `stops.txt`
- `stop_times.txt`
- `trips.txt`
- `routes.txt`
- `shapes.txt`

O grafo passa a incluir:

- **nós de parada** (com `stop_id`),
- **arestas `bus`** entre paradas consecutivas de uma mesma viagem,
- **arestas `walk`** ligando paradas ao grafo viário (acesso/egresso).

Se algum arquivo faltar, o fallback ignora o GTFS e mantém só os modais derivados do OSM.

---

## API de Clima (Open-Meteo)

Implementada em [loaders/weather_api.py](../apps/engine/loaders/weather_api.py). Não requer chave.

**Endpoint usado:** `https://api.open-meteo.com/v1/forecast` com `precipitation`, `rain`.

**Mapeamento precipitação → `rain_factor`:**

| Precipitação (mm) | `rain_factor` |
|-------------------|---------------|
| 0                 | 1.0           |
| < 2.5             | 1.2           |
| < 10              | 1.5           |
| < 50              | 2.0           |
| ≥ 50              | 2.5           |

`tide_factor` é uma heurística baseada em horário (não consulta API externa).

Ambos multiplicam o tempo de cada aresta e ajustam risco.

---

## Cache do Grafo

`apps/engine/apps/engine/cache/` (gitignored) guarda o grafo OSMnx serializado mais os dados de velocidade. Primeira execução demora minutos baixando e processando "Recife, Brazil"; execuções seguintes carregam em segundos.

Para invalidar manualmente: `rm -rf apps/engine/cache/`.

---

## Fontes recomendadas

- **OSMnx** já cuida do OpenStreetMap automaticamente.
- **GTFS de Recife:** disponibilizado pelo Grande Recife Consórcio de Transporte (`granderecife.pe.gov.br`).
- **CSVs de risco/custo:** combinação de dados públicos (SDS-PE para crime, Detran-PE para acidentes) e tabelas de referência. Estrutura exata dos CSVs: ver os parsers em `loaders/csv_loader.py`.
