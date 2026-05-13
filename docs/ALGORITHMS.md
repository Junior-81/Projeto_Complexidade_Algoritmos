# Algoritmos: Dijkstra e A\*

Este documento explica como os dois algoritmos são aplicados ao grafo multimodal e quando cada um faz mais sentido.

---

## Modelagem

O problema é transformado em **caminho mínimo em grafo ponderado**. O grafo:

- **Nós:** interseções de ruas + paradas de ônibus.
- **Arestas:** uma cópia da rua para cada modal possível, mais arestas de bus a partir do GTFS.
- **Estado de busca:** `(node_id, modal_atual, used_bus)` — não apenas o nó, porque trocas de modal e obrigatoriedade de ônibus afetam o caminho válido.

---

## Função Objetivo (peso de aresta)

```
tempo_norm = (tempo - tempo_min) / (tempo_max - tempo_min)
custo_norm = (custo - custo_min) / (custo_max - custo_min)
risco_norm = (risco - risco_min) / (risco_max - risco_min)

peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
```

A normalização **Min-Max** existe porque tempo (horas), custo (R$) e risco (índice adimensional) vivem em escalas diferentes. Sem ela, a métrica de maior magnitude dominaria a decisão.

Os intervalos `[min, max]` são calibrados antes da busca, amostrando até 80.000 arestas reais do grafo (`graph.normalizer.Normalizer`).

---

## Dijkstra

Implementação: [routing/dijkstra_multimodal.py](../apps/engine/routing/dijkstra_multimodal.py).

Prioridade na fila:
```
prioridade = g(n)   # custo acumulado real
```

**Propriedades:**

- Ótimo garantido para pesos não negativos (✓ — todos os pesos aqui são ≥ 0).
- Tende a expandir mais estados que A\* porque não "olha para o destino".
- **Default do projeto.**

---

## A\*

Implementação: [routing/astar_multimodal.py](../apps/engine/routing/astar_multimodal.py).

Prioridade na fila:
```
f(n) = g(n) + h(n)
```

### Heurística usada

```
h(n) = haversine(n, destino) / velocidade_maxima_disponivel
```

Depois normalizada para a mesma escala do peso (Min-Max).

A heurística é **admissível** enquanto `velocidade_maxima_disponivel` for de fato um teto — ou seja, ela nunca superestima o tempo real até o destino. Como custo e risco também contam no peso, a heurística é, no pior caso, otimista também nesses eixos (`h_custo = h_risco = 0`).

### Propriedades

- Geralmente expande menos estados que Dijkstra em grafos grandes.
- Mantém qualidade da rota desde que a heurística não superestime.

---

## Quando usar cada um

| Cenário | Algoritmo |
|---------|-----------|
| Baseline conservador, comparação acadêmica | `dijkstra` |
| Grafos grandes onde performance importa | `astar` |
| Reproduzir resultado independente de heurística | `dijkstra` |

Ambos retornam o mesmo caminho ótimo quando a heurística de A\* é admissível — A\* só **explora menos**.

---

## Restrições de Modal

Implementadas em `core.restrictions`. O parâmetro `restricao_modal` controla:

| Valor | `allowed_modes` | `bus_required` | `max_walk_distance_km` | `walk_penalty_factor` |
|-------|-----------------|----------------|------------------------|-----------------------|
| `walk` / `bike` / `car` / `moto` / `bus` / `uber_car` / `uber_moto` | `{aquele}` | False | — | 1.0 |
| `bus_com_acesso` | `{walk, bus}` | True | 0.5 | 1.4 |
| `bus_estrito` | `{bus}` | False | — | 1.0 |
| (omitido) | None (livre) | False | — | 1.0 |

Quando `bus_required = True`, a busca só aceita estados-meta com `used_bus = True`.

Quando `max_walk_distance_km` é definido, arestas de `walk` mais longas são **descartadas** durante a expansão.

`walk_penalty_factor` multiplica o peso da aresta walk — encarece caminhar quando o objetivo é forçar uso de ônibus, sem inviabilizar totalmente trechos curtos de acesso/egresso.

---

## Reconstrução da Rota

Após a busca, [routing/path_reconstructor.py](../apps/engine/routing/path_reconstructor.py) percorre o caminho `[(node, modal, used_bus), ...]` e:

1. Agrupa arestas consecutivas do **mesmo modal** em um segmento.
2. Para Uber, agrupa por `meio` (`uber carro` ou `uber moto`) para cobrar como corrida contínua.
3. Para bus, anexa `linha`, `gtfs_shape_id`, `validacao_gtfs`.
4. Calcula `tempo`, `distancia`, `custo`, `velocidade_media_kmh` por segmento.
5. Soma totais em `resumo`.

---

## Complexidade

Sendo `V` o número de estados (`nós × modais`) e `E` o número de arestas:

- **Dijkstra com heap binário:** `O((V + E) log V)`.
- **A\* com heap binário:** mesmo pior caso, mas na prática expande uma fração dos estados de Dijkstra graças à heurística.

Para o grafo de Recife com ~6 modais replicados, `V` está na ordem de 10⁵ e `E` na ordem de 10⁶. A normalização Min-Max é `O(E)` amortizado uma vez por execução (capada em 80k arestas).
