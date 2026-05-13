# Projeto de Complexidade de Algoritmos

Repositório da disciplina **Análise, Projeto e Complexidade de Algoritmos**. Contém:

1. **[Sistema de Rotas Multimodais](#sistema-de-rotas-multimodais)** — projeto principal: monorepo (Turborepo) com motor de roteamento Dijkstra/A\* sobre grafo multimodal em Recife.
2. **[Atividade: Busca de Matrículas](#atividade--busca-de-matrículas-lista-comentada)** — lista comentada sobre busca linear, binária e hash.

---

# Sistema de Rotas Multimodais

Monorepo (Turborepo) com um motor de roteamento que recomenda rotas urbanas em Recife otimizando **tempo, custo e risco** simultaneamente via **Dijkstra** ou **A\***.

```
peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
```

Modais: `walk`, `bike`, `car`, `moto`, `bus`, `uber_car`, `uber_moto`.

---

## Estrutura (monorepo)

```
.
├── package.json              # workspaces npm
├── turbo.json                # task graph
│
├── apps/
│   ├── engine/               # @rotas/engine — motor Python (Dijkstra/A*)
│   │   ├── main.py           # CLI
│   │   ├── core/             # pipeline puro (run_route)
│   │   ├── graph/            # construção do grafo
│   │   ├── routing/          # algoritmos
│   │   ├── loaders/          # CSV + Open-Meteo
│   │   ├── scripts/          # utilitários (visualize_route.py)
│   │   ├── data/             # CSVs + GTFS (não versionado)
│   │   ├── cache/            # grafo serializado (não versionado)
│   │   ├── output/           # resultados (não versionado)
│   │   ├── input.json
│   │   └── requirements.txt
│   │
│   ├── api/                  # @rotas/api — FastAPI, importa engine in-process
│   │   ├── app/main.py
│   │   └── requirements.txt
│   │
│   └── web/                  # @rotas/web — React + Vite + Leaflet
│       ├── src/
│       └── package.json
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ALGORITHMS.md
│   ├── DATA.md
│   └── lista-busca-matriculas/  # código da atividade (Parte 2)
│       ├── busca.py
│       └── resultado_execucao.txt
│
├── CLAUDE.md
└── README.md
```

---

## Como rodar (Sistema de Rotas)

### Setup

```bash
# JS workspaces
npm install

# Python (engine + api)
pip install -r apps/engine/requirements.txt
pip install -r apps/api/requirements.txt
```

### Desenvolvimento

```bash
npm run dev          # roda tudo em paralelo (turbo)
```

Ou cada app isolado:

```bash
npm run dev --workspace=@rotas/web      # http://localhost:5173
npm run dev --workspace=@rotas/api      # http://localhost:8000
npm run calc --workspace=@rotas/engine  # roda main.py
```

### Comandos úteis

| Comando | Ação |
|---------|------|
| `npm run calc` | Executa o motor (`apps/engine/main.py`) com `input.json` |
| `npm run visualize` | Gera `apps/engine/output/route_map.html` |
| `npm run build` | Build do frontend |
| `npm run start` | Servir versões de produção (web + api) |

---

## Entrada / Saída

`apps/engine/input.json`:

```json
{
  "origem": [-8.062742, -34.8739],
  "destino": [-8.117809, -34.900231],
  "modo_inicial": "walk",
  "algoritmo": "dijkstra",
  "restricao_modal": "bus_com_acesso"
}
```

- `modo_inicial`: `walk | bike | car | moto | bus | uber_car | uber_moto`
- `algoritmo`: `dijkstra` (default) | `astar`
- `restricao_modal` (opcional): modal único, `bus_com_acesso` (walk + bus, walk ≤ 0.5km) ou `bus_estrito`

Saída em `apps/engine/output/output.json`: lista de `edges`, `segments` e `resumo`.

---

## API (FastAPI)

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/health` | Status + caminhos |
| `GET /api/route` | Último `output.json` |
| `POST /api/calculate` | Recalcula com o payload e devolve a rota |
| `POST /api/options` | Roda 9 cenários e devolve ranking |

O backend importa `core.pipeline.run_route` **in-process** — o cache do grafo OSMnx fica em memória entre requests.

---

## Documentação técnica

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — fluxo do pipeline e componentes.
- [docs/ALGORITHMS.md](docs/ALGORITHMS.md) — Dijkstra vs A\*, função objetivo, heurística, restrições.
- [docs/DATA.md](docs/DATA.md) — CSVs esperados, GTFS, API de clima.

---

## Dependências

**Engine (Python):** `osmnx`, `networkx`, `pandas`, `numpy`, `geopandas`, `requests`, `folium`.

**API (Python):** `fastapi`, `uvicorn`, `pydantic`.

**Web (Node):** `react`, `vite`, `leaflet`, `react-leaflet`.

**Monorepo (Node):** `turbo`.

---

## Troubleshooting

| Sintoma | Causa provável |
|---------|----------------|
| `No module named pandas` | Faltou `pip install -r apps/engine/requirements.txt` |
| `uvicorn não reconhecido` | Use `python -m uvicorn ...` ou `npm run dev --workspace=@rotas/api` |
| Front sem resposta | Backend não está em `:8000`. Teste `GET /api/health` |
| Primeira execução lenta | Download/processamento do OSMnx; runs seguintes usam `apps/engine/cache/` |
| Avisos sobre `data/` | Sistema tem fallbacks, mas resultado fica mais realista com CSVs e GTFS completos |

---
---

# Atividade — Busca de Matrículas (Lista Comentada)

**Estudo de caso:** busca de matrículas em uma secretaria acadêmica.
**Código rodável:** [docs/lista-busca-matriculas/busca.py](docs/lista-busca-matriculas/busca.py)

## Situação-problema

Uma secretaria acadêmica possui uma lista de matrículas de estudantes e precisa consultar se uma matrícula específica está cadastrada.

```
Lista: [2023001, 2023045, 2023102, 2023120, 2023201, 2023333]
Pergunta: a matrícula 2023102 está cadastrada?
```

---

## Parte A — Análise inicial

### 1. Qual é a entrada do problema?

A entrada são **dois elementos**:

1. uma **lista de matrículas** já cadastradas;
2. uma **matrícula procurada**.

> Sem esses dois dados, o algoritmo não saberia onde procurar nem o que procurar.

### 2. Qual é a saída esperada?

Um valor **booleano**: `verdadeiro` se a matrícula estiver cadastrada, `falso` caso contrário.

> A questão não pede a posição da matrícula — apenas a existência.

### 3. O problema exige uma ou várias consultas?

Pode envolver tanto uma única consulta quanto várias.

> Essa distinção é crucial: para poucas consultas, uma estratégia simples basta. Para muitas, vale o custo de preparar a estrutura uma vez para acelerar o restante.

### 4. O tamanho da lista influencia o desempenho?

**Sim.** Quanto maior a lista, mais cara fica a busca item-por-item. Em uma lista pequena qualquer estratégia é instantânea; em listas grandes, a diferença assintótica entre O(n), O(log n) e O(1) é decisiva.

---

## Parte B — Projeto dos algoritmos (pseudocódigo)

### Solução 1 — Busca Linear

```
funcao busca_linear(lista, alvo):
    para cada matricula em lista:
        se matricula == alvo:
            retornar verdadeiro
    retornar falso
```

- **Estratégia:** percorre a lista do início ao fim.
- **Pior caso:** verifica todos os `n` elementos.
- **Complexidade:** `O(n)`.

### Solução 2 — Busca Binária

```
funcao busca_binaria(lista, alvo):
    ordenar lista
    inicio <- 0
    fim    <- tamanho(lista) - 1
    enquanto inicio <= fim:
        meio <- (inicio + fim) / 2
        se lista[meio] == alvo:
            retornar verdadeiro
        senao se alvo < lista[meio]:
            fim    <- meio - 1
        senao:
            inicio <- meio + 1
    retornar falso
```

- **Requisito:** a lista precisa estar **ordenada**.
- **Estratégia:** divide o espaço de busca pela metade a cada iteração.
- **Complexidade da ordenação:** `O(n log n)`.
- **Complexidade da busca:** `O(log n)`.

### Solução 3 — Estrutura Hash

```
funcao busca_hash(lista, alvo):
    conjunto <- conjunto vazio
    para cada matricula em lista:
        inserir matricula em conjunto
    retornar (alvo pertence a conjunto)
```

- **Estratégia:** insere todos os elementos em uma estrutura indexada por hash.
- **Complexidade da construção:** `O(n)`.
- **Complexidade média de cada consulta:** `O(1)`.
- **Tradeoff:** ocupa mais memória; só vale a pena quando o conjunto será consultado várias vezes.

---

## Parte C — Implementação

Código rodável em [docs/lista-busca-matriculas/busca.py](docs/lista-busca-matriculas/busca.py).

```python
def busca_linear(lista, alvo):
    for item in lista:
        if item == alvo:
            return True
    return False


def busca_binaria(lista, alvo):
    lista = sorted(lista)
    inicio, fim = 0, len(lista) - 1
    while inicio <= fim:
        meio = (inicio + fim) // 2
        if lista[meio] == alvo:
            return True
        if alvo < lista[meio]:
            fim = meio - 1
        else:
            inicio = meio + 1
    return False


def busca_hash(lista, alvo):
    return alvo in set(lista)
```

---

## Parte D — Análise de complexidade

| Estratégia    | Preparação   | Consulta (média) | Total para 1 consulta | Quando usar |
|---------------|--------------|------------------|-----------------------|-------------|
| Busca linear  | `O(1)`       | `O(n)`           | `O(n)`                | Poucos dados ou poucas consultas |
| Busca binária | `O(n log n)` | `O(log n)`       | `O(n log n + log n)`  | Lista já ordenada ou muitas consultas |
| Hash (`set`)  | `O(n)`       | `O(1)` em média  | `O(n)`                | Muitas consultas rápidas |

**Leitura:**

- A busca linear **não paga custo de preparação**, mas cada consulta cresce linearmente.
- A busca binária paga `O(n log n)` na ordenação inicial; depois cada consulta é barata.
- A estrutura hash paga `O(n)` para construir; depois cada consulta é, em média, **constante**.

> No pior caso da hash há colisões e a consulta degrada para `O(n)`, mas com uma função de hash razoável isso é muito raro em prática.

---

## Parte E — Escolha por cenário

| Cenário | Melhor escolha | Justificativa |
|---------|----------------|---------------|
| **1 consulta por dia** | Busca linear | Não compensa pagar `O(n log n)` para ordenar nem `O(n)` para montar a hash se só haverá uma consulta. `O(n)` resolve. |
| **500 consultas por dia** | Busca binária **ou** `set` | A preparação se amortiza: `500 × O(log n)` ou `500 × O(1)` superam folgadamente `500 × O(n)` da busca linear. |
| **50.000 consultas por dia** | `set` (hash) | A construção `O(n)` se paga em milhares de consultas `O(1)`. A binária ainda é boa, mas o `log n` se torna pior que o `1` médio da hash. |

---

## Conclusão (Atividade)

- **Busca linear:** simples, mas escala mal.
- **Busca binária:** rápida, mas exige lista ordenada.
- **Hash (`set`):** consulta média constante, mas precisa construir a estrutura antes e usa mais memória.

A escolha **não é sobre qual algoritmo é "melhor"**, e sim sobre a **relação entre tamanho da lista e quantidade de consultas**:

- Poucas consultas → busca linear.
- Muitas consultas → preparar a estrutura compensa (binária ou hash).
- Quando o número de consultas é muito alto, **hash domina** porque `O(1)` médio vence `O(log n)` no longo prazo.

---

## Como executar (Atividade)

### Pré-requisitos

- Python 3.8 ou superior. Verifique com `python3 --version`.
- Nada além disso — o script usa só biblioteca padrão (`random`, `time`).

### Forma 1 — Executar tudo de uma vez (recomendado)

A partir da raiz do projeto:

```bash
python3 docs/lista-busca-matriculas/busca.py
```

Roda **a demonstração + o benchmark** em sequência.

### Forma 2 — Executar de dentro da pasta da atividade

```bash
cd docs/lista-busca-matriculas
python3 busca.py
```

Equivalente à Forma 1, só muda o diretório de trabalho.

### Forma 3 — Executar e salvar a saída em arquivo

```bash
python3 docs/lista-busca-matriculas/busca.py > docs/lista-busca-matriculas/resultado_execucao.txt
```

Ou, para ver no terminal **e** salvar ao mesmo tempo:

```bash
python3 docs/lista-busca-matriculas/busca.py | tee docs/lista-busca-matriculas/resultado_execucao.txt
```

### Forma 4 — Testar as funções individualmente (Python interativo)

Útil para experimentar com outras listas e outras matrículas:

```bash
cd docs/lista-busca-matriculas
python3
```

Dentro do interpretador:

```python
>>> from busca import busca_linear, busca_binaria, busca_hash
>>> lista = [2023001, 2023045, 2023102, 2023120, 2023201, 2023333]
>>>
>>> busca_linear(lista, 2023102)
True
>>> busca_binaria(lista, 2023102)
True
>>> busca_hash(lista, 2023102)
True
>>>
>>> busca_linear(lista, 9999999)   # matrícula inexistente
False
```

### Forma 5 — Rodar só uma parte (demonstração OU benchmark)

Se quiser pular o benchmark e ver só a demonstração do enunciado:

```bash
cd docs/lista-busca-matriculas
python3 -c "from busca import demonstracao_enunciado; demonstracao_enunciado()"
```

Se quiser só o benchmark (configurando o tamanho da lista e o número de consultas):

```bash
python3 -c "from busca import benchmark; benchmark(n=100_000, consultas=500)"
```

Você pode trocar os valores. Sugestões para comparar:

| `n`        | `consultas` | O que observar |
|------------|-------------|----------------|
| `1_000`    | `10`        | Tudo é rápido — diferença quase imperceptível |
| `100_000`  | `500`       | Diferença clara: linear ~470 ms, binária ~35 ms, hash ~11 ms |
| `1_000_000`| `1_000`     | Linear fica desconfortavelmente lenta (segundos) |

---

## Resultado da execução

Saída completa de uma execução real (também disponível em [docs/lista-busca-matriculas/resultado_execucao.txt](docs/lista-busca-matriculas/resultado_execucao.txt)):

```
============================================================
Lista:     [2023001, 2023045, 2023102, 2023120, 2023201, 2023333]
Procurar:  2023102 (esperado: True)
============================================================
  busca_linear  -> True
  busca_binaria -> True
  busca_hash    -> True

Procurar:  2024999 (esperado: False)
  busca_linear  -> False
  busca_binaria -> False
  busca_hash    -> False

============================================================
Benchmark: lista com 100,000 matrículas, 500 consultas
============================================================
  Linear  :   469.47 ms
  Binária :    35.92 ms  (inclui ordenação inicial)
  Hash    :    11.49 ms  (inclui construção do set)

Observe a relação:
  Linear / Hash    ≈ 41x
  Linear / Binária ≈ 13x
```

### Leitura dos números

- A matrícula do enunciado (`2023102`) é encontrada pelas três estratégias; uma matrícula inexistente (`2024999`) é corretamente rejeitada — todas estão corretas.
- No benchmark, a busca linear precisa varrer ~50.000 elementos em média por consulta; multiplicado por 500 consultas, isso explica os ~470 ms.
- A busca binária só faz ~17 comparações por consulta (`log₂ 100.000 ≈ 17`), e a hash faz **uma** consulta direta em média.
- Os tempos absolutos variam entre execuções (depende da carga da máquina); a **proporção** entre as estratégias é o que importa e se mantém estável.
