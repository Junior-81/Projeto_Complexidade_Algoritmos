# Funcionamento Atual do Sistema

## 1. Objetivo
O sistema calcula uma rota multimodal entre origem e destino, equilibrando tempo, custo e risco com A* em um grafo construído com OSMnx e enriquecido com dados locais (CSV), GTFS e clima.

## 2. Entradas e dados carregados

### 2.1 Entrada principal
- `input.json`
  - `origem`: latitude/longitude de partida
  - `destino`: latitude/longitude de chegada
  - `modo_inicial`: modal inicial (ex.: walk)

### 2.2 Arquivos CSV carregados
Carregados pelo `CSVLoader` a partir de `data/`:
- `crime_rate.csv`: risco de assalto por modal
- `accident_rate.csv`: risco de acidente por modal
- `fuel_consumption.csv`: consumo de combustivel e custo por km (quando aplicavel)
- `uber_price_ranges.csv`: parametros de referencia do Uber
- `transport_speed.csv`: velocidade media por modal
- `flood_risk_streets.csv`: multiplicadores de alagamento por rua
- `weather_factors.csv`: disponivel para extensao
- `tide_factors.csv`: disponivel para extensao

### 2.3 GTFS de onibus
Lido em `data/bus_gtfs/`:
- `shapes.txt`
- `trips.txt`
- `routes.txt`

Esses arquivos validam e adicionam trechos reais de onibus ao grafo multimodal.

### 2.4 API de clima
- Open-Meteo (`WeatherAPI`)
- Retorna `precipitation`, `rain`, `rain_factor`
- O sistema calcula tambem `tide_factor` por heuristica de horario

## 3. Tratamento e processamento dos dados

## 3.1 Risco por modal
`RiskCalculator` combina:
- Risco de crime (normalizado pelo maximo de roubos)
- Risco de acidente (deaths/involved)

Composicao:
- 50% crime
- 50% acidente

Depois aplica defaults para modais sem dado suficiente (incluindo `uber_car` e `uber_moto`).

## 3.2 Custo por modal
`CostCalculator` aplica regras diferentes por modal:
- walk: custo zero
- bike: custo por km (CSV)
- bus: tarifa fixa (R$ 4.50)
- car/moto proprios: consumo de combustivel x preco da gasolina
- uber_car/uber_moto: formula dinamica

Gasolina para veiculo proprio:
- Definida em constante no `main.py`
- `GASOLINE_PRICE_PER_LITER = 7.50`

### Formula de Uber usada
Preco final:

`preco = base + (distancia_km * valor_km) + (tempo_min * valor_min)`

Com faixas por servico:
- Uber carro:
  - base: 3.00
  - km: 1.10 a 1.60
  - minuto: 0.20 a 0.40
- Uber moto:
  - base: 2.00
  - km: 0.60 a 1.00
  - minuto: 0.05 a 0.20

A selecao dentro da faixa usa um indice dinamico (`surge_index`) com pesos de:
- clima (rain_factor)
- transito (inferido pela velocidade media)
- oferta de motorista (heuristica por horario)

## 3.3 Grafo multimodal
`GraphBuilder`:
1. Baixa grafo viario de Recife com OSMnx.
2. Replica arestas para modais:
   - `walk`, `bike`, `car`, `moto`, `uber_car`, `uber_moto`
3. Em cada aresta motorizada, tenta usar `maxspeed` do OSM (quando existir).
4. Quando `maxspeed` nao existir ou for invalido, usa fallback de 50 km/h.
5. Integra GTFS adicionando arestas de `bus` com:
   - `line`
   - `gtfs_shape_id`
   - `source=gtfs`

## 3.4 Normalizacao (Min-Max)
`Normalizer` coleta amostras de tempo, custo e risco para construir intervalos min/max.

Esses intervalos sao usados para normalizar cada aresta durante a busca A*.

## 3.5 Busca A* multimodal
`AStarMultimodal` usa estado:
- `(node, modal_atual)`

Para cada transicao:
1. Calcula tempo da aresta com velocidade do OSMnx (ou fallback 50 km/h em modais motorizados).
2. Calcula custo via `CostCalculator`.
3. Calcula risco acumulado por distancia.
4. Normaliza tempo, custo e risco.
5. Aplica funcao objetivo multiobjetivo:

`peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm`

Heuristica:
- distancia em linha reta / velocidade maxima esperada

Restricao implementada:
- Se `modo_inicial` for `walk`, o algoritmo evita trocar para veiculo proprio (`car`/`moto`) e prioriza meios publicos/app (`bus`, `uber_car`, `uber_moto`, etc.).

## 3.6 Reconstrucao da rota
`PathReconstructor`:
1. Agrupa arestas consecutivas do mesmo modal.
2. Calcula distancia, tempo, velocidade media e custo por segmento.
3. Para Uber, preserva agrupamento por meio (`uber_car` ou `uber_moto`) para cobrar como corrida continua do mesmo tipo.
4. Para onibus, inclui marcadores de validacao GTFS.

Campos adicionais por segmento:
- `meio`: ex. `uber carro`, `uber moto`
- `velocidade_media_kmh`
- `linha`, `gtfs_shape_id`, `validacao_gtfs` (quando bus)

## 4. Como chega ao output JSON
No final do fluxo, `main.py` salva `output.json` com:

- `rota`: lista de segmentos agregados
- `resumo`: consolidado da viagem

### Estrutura atual da saida
- Em `rota` (por segmento):
  - `modo`
  - `meio`
  - `origem`
  - `destino`
  - `tempo`
  - `distancia`
  - `velocidade_media_kmh`
  - `custo`
  - campos extras por modal (`servico`, `linha`, `gtfs_shape_id`, `validacao_gtfs`)

- Em `resumo`:
  - `tempo_total`
  - `custo_total`
  - `distancia_total`
  - `velocidade_media_kmh`
  - `risco_medio`

## 5. Fluxo resumido (pipeline)
1. Le `input.json`
2. Carrega CSVs
3. Calcula riscos
4. Configura custos e velocidades
5. Busca clima e mare
6. Monta grafo multimodal OSM
7. Integra onibus GTFS
8. Normaliza tempo/custo/risco
9. Executa A*
10. Reconstrui segmentos e resumo
11. Salva `output.json`
