# Sistema de Recomendação de Rotas Multimodais Com A*

Um sistema avançado em Python para encontrar a melhor rota entre dois pontos considerando múltiplos modais de transporte, usando o algoritmo A* e otimização multiobjetivo.

## Características

✅ **Otimização Multiobjetiva**: Considera tempo, custo e risco na mesma decisão  
✅ **Algoritmo A*** com heurística euclidiana adaptada  
✅ **Grafo Multimodal**: De walk, bike, car, moto, bus e uber  
✅ **Dados Climáticos**: Integração com API Open-Meteo para fatores de chuva  
✅ **Análise de Risco**: Cálculo de risco baseado em crime e acidentes por modal  
✅ **Normalização Min-Max**: Para comparação justa entre objetivos  
✅ **Saída em JSON**: Com detalhes da rota e resumo dos métricas  

## Estrutura do Projeto

```
project/
│
├── data/                         # Arquivos CSV com dados
│   ├── crime_rate.csv           # Taxa de assaltos por modal
│   ├── accident_rate.csv        # Taxa de acidentes por modal
│   ├── fuel_consumption.csv     # Consumo e custo de combustível
│   ├── uber_price_ranges.csv    # Preços do Uber por faixa de km
│   ├── transport_speed.csv      # Velocidade média por modal
│   ├── flood_risk_streets.csv   # Ruas com risco de alagamento
│   ├── weather_factors.csv      # Fatores de chuva
│   └── tide_factors.csv         # Fatores de maré
│
├── loaders/                      # Módulos de carregamento de dados
│   ├── __init__.py
│   ├── csv_loader.py            # Carregador de CSVs
│   └── weather_api.py           # API de clima
│
├── graph/                        # Componentes de construção de grafo
│   ├── __init__.py
│   ├── graph_builder.py         # Construtor do grafo com OSMnx
│   ├── risk_calculator.py       # Calculador de riscos
│   ├── cost_calculator.py       # Calculador de custos
│   └── normalizer.py            # Normalizador Min-Max
│
├── routing/                      # Algoritmos de roteamento
│   ├── __init__.py
│   ├── astar_multimodal.py      # Implementação do A*
│   └── path_reconstructor.py    # Reconstrutor de rotas
│
├── main.py                       # Ponto de entrada principal
├── input.json                    # Arquivo de entrada com origem/destino
├── output.json                   # Arquivo de saída com a rota
└── requirements.txt              # Dependências Python
```

## Instalação

1. **Clone ou descompacte o projeto**

2. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare o arquivo de entrada** (`input.json`):
   ```json
   {
     "origem": [-8.05, -34.90],
     "destino": [-8.10, -34.95],
     "modo_inicial": "walk"
   }
   ```
   - `origem`: [latitude, longitude] do ponto de partida
   - `destino`: [latitude, longitude] do ponto de chegada
   - `modo_inicial`: walk | bike | car | moto (determina se pode trocar de modal)

## Uso

Execute o sistema:

```bash
python main.py
```

### Modo especial: bus_com_acesso

Para evitar falso negativo de `bus-only`, o projeto agora suporta `restricao_modal: "bus_com_acesso"`.

Observacao: `restricao_modal: "bus"` usa o mesmo comportamento de acesso a pe (compatibilidade para frontend/API).

- Modais permitidos neste modo: `walk` e `bus`
- Regra obrigatória: a rota so e aceita se usar `bus` em pelo menos um trecho
- Regras de caminhada neste modo:
  - limite por aresta: `0.5 km`
  - penalizacao no peso da aresta: `x1.4`

Exemplo de entrada:

```json
{
  "origem": [-8.05, -34.90],
  "destino": [-8.10, -34.95],
  "modo_inicial": "walk",
  "restricao_modal": "bus_com_acesso"
}
```

### Evidencia tecnica (29/03/2026)

Comando executado:

```bash
POST /api/calculate
{
  "restricao_modal": "bus_com_acesso"
}
```

Resultado observado:

- Status HTTP: `200`
- Arestas na rota: `91`
- Segmentos: `3`
- Modais presentes: `bus` e `walk`

## GTFS operacional com paradas (stops)

O integrador GTFS foi evoluido para priorizar modelo operacional:

`walk -> stop -> bus -> stop -> walk`

Arquivos usados no feed GTFS local:

- `data/bus_gtfs/stops.txt`
- `data/bus_gtfs/stop_times.txt`
- `data/bus_gtfs/trips.txt`
- `data/bus_gtfs/routes.txt`

Comportamento implementado:

- cria nos de parada (`type=stop`) no grafo multimodal;
- cria arestas `bus` por sequencia real de `stop_sequence` em `stop_times`;
- conecta rua <-> parada por `walk` dentro de raio maximo de `0.5 km`;
- se `stops/stop_times` nao existirem, aplica fallback para modo shape-based.

### Evidencia tecnica (29/03/2026 - stop-based)

Comando executado:

```bash
POST /api/calculate
{
  "restricao_modal": "bus_com_acesso"
}
```

Resultado observado apos stop-based:

- Status HTTP: `200`
- Arestas na rota: `7`
- Segmentos: `3`
- Modais presentes: `bus` e `walk`
- Distancia total: `9.9862 km`
- Tempo total: `0.6388 h`

O sistema irá:

1. Ler o arquivo `input.json`
2. Carregar dados dos CSVs
3. Calcular riscos por modal
4. Obter dados climáticos da API aberta
5. Construir o grafo multimodal com OSMnx
6. Executar o algoritmo A*
7. Gerar o arquivo `output.json` com a rota recomendada

## Saída (output.json)

```json
{
  "rota": [
    {
      "modo": "walk",
      "origem": [-8.05, -34.90],
      "destino": [-8.065, -34.905],
      "tempo": 5.2,
      "distancia": 0.43,
      "custo": 0.0
    },
    {
      "modo": "bus",
      "origem": [-8.065, -34.905],
      "destino": [-8.10, -34.95],
      "tempo": 18.5,
      "distancia": 7.2,
      "custo": 4.50
    }
  ],
  "resumo": {
    "tempo_total": 23.7,
    "custo_total": 4.50,
    "distancia_total": 7.63,
    "risco_medio": 0.156
  }
}
```

## Algoritmo A*

O algoritmo implementa A* multimodal com:

- **Estado**: (nó_no_grafo, modal_atual)
- **Heurística**: Distância euclidiana / velocidade máxima
- **Função Objetivo** (peso da aresta):
  ```
  peso = 0.5 * tempo_normalizado +
         0.3 * custo_normalizado +
         0.2 * risco_normalizado
  ```

## Cálculos

### Risco
- Baseia-se em assaltos (crime_rate) e acidentes (accident_rate)
- Normalizado entre 0 e 1 usando Min-Max
- Multiplicado pela distância para acumular

### Tempo
```
tempo_base = distancia_km / velocidade_kmh
tempo_final = tempo_base * fator_chuva * fator_mare * multiplicador_rua
```

### Custo
- walk: R$ 0
- bike: R$ 0.01/km (ou valor do CSV)
- bus: R$ 4.50 (tarifa fixa)
- car/moto: (distancia / km_por_litro) * preco_gasolina
- uber: distancia * preco_por_km

## Dados Esperados

### CSVs Mínimos:
- `crime_rate.csv`: mode, robberies
- `accident_rate.csv`: mode, deaths, involved
- `transport_speed.csv`: mode, speed_kmh
- `fuel_consumption.csv`: mode, km_per_liter
- `uber_price_ranges.csv`: car_price_per_km, moto_price_per_km
- `flood_risk_streets.csv`: street_name, rain_multiplier

### Dados de Exemplo:

**crime_rate.csv**:
```
mode,robberies
walk,10345
bike,21
car,3651
moto,3651
bus,229
```

**transport_speed.csv**:
```
mode,speed_kmh
walk,5
bike,15
car,40
moto,45
bus,25
```

## Extensões Possíveis

- [ ] Adicionar suporte a metrô/trem com GTFS
- [ ] Implementar Dijkstra como alternativa
- [ ] Cache de grafo para rotas frequentes
- [ ] Interface web com Flask/Streamlit
- [ ] Visualização interativa com folium
- [ ] Integração com OpenStreetMap para ruas em tempo real
- [ ] Suporte a restrições de horário (madrugada, feriados)
- [ ] Feedback de usuários para melhorar pesos

## Requisitos do Sistema

- Python 3.8+
- Acesso à internet (para Open-Meteo API)
- ~500MB de RAM para grafos de cidades grandes

## Limitações Conhecidas

1. Grafo carregado em memória (limite em cidades muito grandes)
2. A* assume custos não-negativos (garantido por pesos normalizados)
3. Sem suporte a horários de ônibus específicos (usa velocidade média)
4. Sem integração com GTFS real (simula com mesmas ruas de carro)

## Licença

MIT License - Use livremente em projetos pessoais e comerciais

## Autor

Sistema desenvolvido como demonstração de algoritmos de grafos e otimização multiobjetiva.

---

**Versão**: 1.0.0  
**Última atualização**: 2024
