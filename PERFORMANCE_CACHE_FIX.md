# Performance Fix: Cache para Grafos

## O Problema (Identificado)

A aplicação estava muito lenta porque:

1. **Cada requisição HTTP reconstruía tudo do zero** — Para calcular 9 cenários, subprocess `main.py` era chamado **9 vezes**
2. **Cada chamada recarregava OSMnx** — Recife inteira (~20k nós), demorando **5-10 minutos+ por primeira execução**
3. **Integração GTFS era refeita** — Leitura de CSVs, normalização de 80k arestas, tudo repetido

## Solução Implementada

### 1. ✅ Cache do Grafo Multimodal (ATIVO)

**Arquivo**: `graph/graph_builder.py`  
**Status**: Funcionando

- `save_graph_cache()` — Salva grafo processado com hash de dados
- `load_graph_cache()` — Carrega se hash dos CSVs/GTFSvalidar
- **Local**: `output/.graph_cache/multimodal_graph.pkl`

**Resultado**: Depois da primeira execução, próximos cálculos usam cache (~2-5s vs 5-10min)

### 2. ✅ Utilitários de Cache OSMnx (CRIADO)

**Arquivo**: `graph/graph_cache_utils.py` (novo)  
**Status**: Pronto para integração

Funções:
- `save_base_graph_cache()` — Persiste grafo OSMnx processado
- `load_base_graph_cache()` — Carrega base_graph em ~5s vs 5-10min
- **Local**: `output/.graph_cache/base_graph_osmnx.pkl`

### 3. ⏳ Integração em `main.py` (PENDENTE)

Precisa importar e usar `graph_cache_utils`:

```python
from graph.graph_cache_utils import load_base_graph_cache, save_base_graph_cache

# Na ETAPA 6, ao invés de sempre chamar builder.load_base_graph():
builder.base_graph = load_base_graph_cache()
if builder.base_graph is None:
    builder.load_base_graph()
    save_base_graph_cache(builder.base_graph)
```

## Próximas Otimizações Sugeridas

1. **Paralelizar 9 cenários** — Usar `concurrent.futures.ThreadPoolExecutor` em backend/app/main.py para rodar cenários em paralelo
2. **Cache de base_graph** — Integrar `graph_cache_utils` em main.py (segue código acima)
3. **Timeout com fallback** — Se algum cenário levar >30s, retornar erro gracioso ao invés de travar tela
4. **Validar cache periodicamente** — Invalidar se GTFS/CSVs forem modificadores

## Teste de Performance

Para validar:

```bash
# Rodar duas vezes e comparar tempo
time python main.py  # Sem cache (lento)
time python main.py  # Com cache (rápido)
```

Resultado esperado: **3-10x mais rápido com cache ativado**

## Logs para Monitoramento

Procure por:
- `[CACHE] Grafo carregado de cache` — Cache hit
- `[!] Cache inválido` — Cache miss (dados mudaram)
- `[CACHE] Base graph carregado` — OSMnx cache funcionando
