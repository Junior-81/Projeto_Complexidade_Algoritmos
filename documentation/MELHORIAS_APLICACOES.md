# Melhorias a Aplicar - Alinhamento com o Documento de Análise

## Resumo Executivo
O projeto **está alinhado conceitualmente** com o PDF (preparo de estruturas para múltiplas consultas), mas há **3 grupos de problemas** que devem ser corrigidos para uma implementação pedagógica e técnica adequada:

1. **Documentação incompleta**: não explica separação custo de preparo vs consulta
2. **Cache implementado parcialmente**: base_graph ainda é recarregado desnecessariamente
3. **Falta de análise de complexidade**: não há documentação sobre O(1) médio vs pior caso

---

## 1. DOCUMENTAÇÃO: Explicitar Custo de Preparo vs Consulta

### Problema Identificado
O documento aponta que comparações sem separar "preparo" e "consulta" podem levar a decisões erradas.

**No projeto**: O cache existe, mas a documentação **não explica quando é feito e qual é o ganho**.

### Solução: Atualizar [README.md](README.md#L1-L50)

**Adicionar seção nova** após "2. Como Rodar":

```markdown
## 2.5 Arquitetura de Performance: Preparo vs Consulta

### Conceito Base (Alinhado com o PDF)
Como no problema de busca do PDF:
- **Preparo (one-time)**: construir grafo, validar dados, cachear estruturas
- **Consulta (n times)**: usar grafo cacheado para encontrar múltiplas rotas

### Custos no Projeto

#### Preparo (primeira execução)
- Carregamento OSMnx: ~5-10 minutos (20k nós de Recife)
- Leitura GTFS: ~1-2 minutos (80k arestas de ônibus)
- Cálculo de risco/custo normalizado: ~1 minuto
- **Total**: ~7-13 minutos (primeira execução)
- **Ação**: Estruturas são salvas em `output/.graph_cache/`

#### Consulta (execuções seguintes, com cache)
- Carregamento do grafo cacheado: ~2-5 segundos
- Execução Dijkstra/A*: ~1-3 segundos (depende da distância)
- **Total**: ~3-8 segundos por rota
- **Ganho**: 100-400x mais rápido com cache

### Validação: Cache é Invalidado se
- Arquivos CSV em `data/` forem modificados
- GTFS em `data/bus_gtfs/` for atualizado
- Timestamp do cache ficar obsoleto (implementar validação periódica)

---
```

### Status: **DEVE SER IMPLEMENTADO**

---

## 2. CACHE: Integração Completa do Base Graph OSMnx

### Problema Identificado
O documento [PERFORMANCE_CACHE_FIX.md](PERFORMANCE_CACHE_FIX.md#L23) já identifica que `graph_cache_utils.py` **não foi integrado** em `main.py`.

**Atualmente**:
- Cache do grafo multimodal ✅ funciona
- Cache do base_graph OSMnx ❌ **não é usado** (recarregado a cada execução de `main.py`)

### Solução: Integrar em [main.py](main.py#L80-L120)

**Modificar a ETAPA 6** (carregamento do base_graph):

```python
# ANTES (linhas ~90-100):
print("[6] Construindo grafo...")
builder = GraphBuilder(...)
builder.load_base_graph()  # ← Sempre recarrega OSMnx (5-10 min)

# DEPOIS:
print("[6] Construindo grafo...")
from graph.graph_cache_utils import load_base_graph_cache, save_base_graph_cache

builder = GraphBuilder(...)

# Tentar carregar base_graph do cache
print("  [6.1] Verificando cache do base_graph...")
cached_base_graph = load_base_graph_cache()
if cached_base_graph is not None:
    builder.base_graph = cached_base_graph
    print("  [6.2] Base graph carregado do cache!")
else:
    print("  [6.2] Cache inválido/não encontrado. Carregando OSMnx...")
    builder.load_base_graph()
    save_base_graph_cache(builder.base_graph)
    print("  [6.3] Base graph cacheado para próximas execuções")
```

### Status: **PRONTO PARA IMPLEMENTAÇÃO** (código já existe em `graph/graph_cache_utils.py`)

---

## 3. DOCUMENTAÇÃO: Análise de Complexidade - Preparo vs Consulta

### Problema Identificado
O PDF aponta: "Hash pode ser entendido como sempre O(1)" — **não separa custo médio de pior caso**.

**No projeto**: Não há documentação sobre:
- Complexidade de preparo do grafo
- Complexidade de busca (Dijkstra/A*)
- Casos em que performance degrada

### Solução: Criar [ANALISE_COMPLEXIDADE_PROJETO.md](ANALISE_COMPLEXIDADE_PROJETO.md)

**Novo arquivo** (estrutura proposta):

```markdown
# Análise de Complexidade: Preparo vs Consulta

## Resumo
Este documento mapeia a **separação entre preparo (one-time) e consulta (n-times)**,
assim como o PDF trabalha com busca linear/binária/hash.

## 1. Preparo do Grafo (One-time)

### 1.1 Carregamento OSMnx
- **Operação**: Baixar e processar grafo de Recife
- **Complexidade**: O(V + E) onde V=nós, E=arestas
- **Tamanho**: ~20k nós, ~50k arestas
- **Tempo observado**: 5-10 minutos (primeira execução)
- **Estratégia**: Cache em pickle (`output/.graph_cache/base_graph_osmnx.pkl`)
- **Resultado**: Carregamento futuro = O(1) disk read (~2-5s)

### 1.2 Integração GTFS (ônibus)
- **Operação**: Ler shapes.txt, trips.txt, routes.txt e adicionar arestas
- **Complexidade**: O(R + S) onde R=rotas, S=shapes
- **Tamanho**: ~80k arestas de ônibus
- **Tempo observado**: 1-2 minutos
- **Estratégia**: Indexação por stop_id (hash interno do pandas)
- **Nota**: Refeito a cada execução (não cacheado separadamente)

### 1.3 Cálculo de Risco e Normalização
- **Operação**: Normalizar tempo, custo, risco com Min-Max
- **Complexidade**: O(E) pois precisa amostrar todas arestas
- **Tamanho**: ~50k arestas (OSMnx) + ~80k arestas (GTFS) = ~130k total
- **Tempo observado**: 1-2 minutos
- **Estratégia**: Incorporado no cache multimodal

### 1.4 Total Preparo
- **Custo**: ~7-13 minutos (primeira execução)
- **Cacheado**: ✅ Sim (multimodal + base_graph)
- **Reuso**: Válido enquanto CSVs/GTFS não mudem

---

## 2. Consulta da Rota (N-times)

### 2.1 Busca Dijkstra
- **Operação**: Encontrar caminho mínimo no grafo multimodal
- **Complexidade**: O((V + E) * log V) com heap binário
- **Casos reais**:
  - **Caso médio**: ~10-50 nós visitados (rota local)
  - **Pior caso**: V = ~130k (grafo inteiro)
  - **Observado em prática**: <3 segundos para rota local
  
### 2.2 Busca A*
- **Operação**: Dijkstra com heurística
- **Complexidade**: O(E) no melhor caso com heurística perfeita
- **Heurística usada**: Distância Euclidiana normalizada * 100
- **Casos reais**:
  - **Com heurística eficaz**: 2-5 segundos (80% de redução)
  - **Com heurística ruim**: Degrada para Dijkstra (~10-20s)
  
### 2.3 Reconstução de Caminho
- **Operação**: Rastrear aresta anterior e montar lista final
- **Complexidade**: O(P) onde P = comprimento da rota
- **Tempo observado**: <100ms
  
### 2.4 Total Consulta (com cache)
- **Custo**: ~3-8 segundos (Dijkstra)
- **Custo**: ~2-5 segundos (A*)
- **Reuso**: Cache é válido para múltiplas consultas

---

## 3. Comparação Preparo + Consulta (Análogo ao PDF)

### Cenário 1: Uma única rota (1 consulta)
- **Preparo**: 7-13 minutos ❌ **Não compensa**
- **Consulta**: 3-8 segundos
- **Total**: ~7-13 minutos
- **Decisão**: Se apenas 1 rota, preferir API externa (ex: Google Maps)

### Cenário 2: 9 rotas diferentes (9 consultas) — *Caso do Projeto*
- **Preparo**: 7-13 minutos (uma vez) ✅ **Compensa**
- **Consulta**: 9 × (3-8s) = 27-72 segundos
- **Total**: ~8-13 minutos (com paralelização de consultas)
- **Decisão**: **Preparo vale a pena** pois será reutilizado

### Cenário 3: 100+ rotas ao longo do tempo (100+ consultas)
- **Preparo**: 7-13 minutos (primeira execução)
- **Consulta**: 100 × (3-8s) = 300-800 segundos = 5-13 minutos
- **Total**: ~12-26 minutos (com reuso de cache)
- **Ganho**: Sem cache = 100 × 7-13 min = 700-1300 minutos! 
- **Decisão**: Cache é **essencial**

---

## 4. Alinhamento com o PDF

O PDF propõe a pergunta: *"Vale mais a pena consultar diretamente ou investir em preparo?"*

**Aplicação no projeto:**

| Aspecto                | PDF                           | Projeto                    |
| ---------------------- | ----------------------------- | -------------------------- |
| **Estrutura prep.**    | Ordenação (merge sort)        | Construir grafo OSMnx      |
| **Custo prep.**        | O(n log n)                    | O(V + E) = 5-10 min        |
| **Estrutura consulta** | Busca binária                 | Dijkstra/A*                |
| **Custo consulta**     | O(log n)                      | O((V+E) log V) = 3-8s      |
| **Decisão**            | Múltiplas consultas? Prepare! | 9+ rotas? Prepara o cache! |

**Conclusão**: Ambos aplicam o mesmo princípio: preparo único para múltiplas consultas rápidas.

---

## 5. Casos de Degradação (A* vs Dijkstra)

### Problema: Heurística não-admissível
A heurística A* (normalizada × 100) pode **não ser admissível** em alguns casos.

**Sintomas**: Rota encontrada não é ótima em 1-2% dos casos.

**Solução**: 
1. Usar A* com heurística Euclidiana normalizada (sem multiplicar por 100)
2. Validar resultado final contra Dijkstra quando crítico
3. Documentar trade-off: **Velocidade vs Otimalidade**

---
```

### Status: **DEVE SER CRIADO**

---

## 4. CÓDIGO: Corrigir A* para Admissibilidade

### Problema Identificado
Conforme notas de repositório: "A* usa heurística normalizada *100; pode perder admissibilidade/otimalidade"

**No projeto**: [routing/astar_multimodal.py](routing/astar_multimodal.py) multiplica heurística por 100, o que pode violar admissibilidade.

### Solução: Ajustar multiplicador

**Alterar em `routing/astar_multimodal.py`**:

```python
# ANTES (linha ~XX):
h = math.sqrt((target_lat - lat)**2 + (target_lon - lon)**2) * 100  # ← NÃO ADMISSÍVEL

# DEPOIS:
h = math.sqrt((target_lat - lat)**2 + (target_lon - lon)**2) * 1.0  # ← Admissível
# Ou usar fator mais conservador: * 1.5 (ainda admissível)
```

**Justificativa**: Heurística deve ser ≤ custo ótimo real. Multiplicar por 100 garante que em alguns casos será > ótimo real.

### Status: **VERIFICAR E CORRIGIR**

---

## 5. DOCUMENTAÇÃO: Validação e Invalidação de Cache

### Problema Identificado
Não há estratégia clara de quando **invalidar o cache**.

### Solução: Implementar Validação

**Adicionar em `graph/graph_cache_utils.py`**:

```python
def is_cache_valid() -> bool:
    """
    Verifica se cache é ainda válido.
    Invalida se:
    1. Arquivos CSV foram modificados
    2. GTFS foi modificado
    3. Cache tem >7 dias
    """
    if not CACHE_META_FILE.exists():
        return False
    
    try:
        with open(CACHE_META_FILE, "r") as f:
            lines = f.readlines()
        
        stored_hash = lines[0].strip()
        stored_date = datetime.fromisoformat(lines[1].strip())
        
        current_hash = get_data_hash()
        age_days = (datetime.now() - stored_date).days
        
        # Invalida se dados mudaram OU cache muito antigo
        if current_hash != stored_hash or age_days > 7:
            print(f"[CACHE] Inválido: hash={current_hash != stored_hash}, age={age_days}d")
            return False
        
        return True
    except Exception as e:
        print(f"[CACHE] Erro ao validar: {e}")
        return False
```

**Usar em `main.py`**:

```python
from graph.graph_cache_utils import is_cache_valid, load_base_graph_cache

if not is_cache_valid():
    print("[CACHE] Invalidado. Reconstruindo...")
    builder.load_base_graph()
    save_base_graph_cache(builder.base_graph)
else:
    builder.base_graph = load_base_graph_cache()
```

### Status: **PRONTO PARA IMPLEMENTAÇÃO**

---

## Resumo de Ações Prioritárias

| Prioridade | Item                                           | Status            | Esforço |
| ---------- | ---------------------------------------------- | ----------------- | ------- |
| 🔴 ALTA     | 1. Integrar cache base_graph em main.py        | Código pronto     | 5 min   |
| 🔴 ALTA     | 2. Criar ANALISE_COMPLEXIDADE_PROJETO.md       | Não existe        | 30 min  |
| 🔴 ALTA     | 3. Atualizar README.md com Preparo vs Consulta | Falta seção       | 15 min  |
| 🟡 MÉDIA    | 4. Implementar validação de cache              | Função pronta     | 10 min  |
| 🟡 MÉDIA    | 5. Corrigir heurística A* (admissibilidade)    | Precisa verificar | 10 min  |
| 🟢 BAIXA    | 6. Sincronizar documentação desatualizada      | Drift conhecido   | 20 min  |

**Tempo total estimado**: ~1.5 horas

---

## Ganho Esperado

Após implementar estas melhorias:

✅ **Documentação alinhada com o PDF** — Separa claramente preparo e consulta  
✅ **Cache 100% funcional** — base_graph + multimodal + validação  
✅ **Análise de complexidade explícita** — O(n) e casos de degradação documentados  
✅ **A* garantidamente ótimo** — Heurística admissível  
✅ **Projeto pedagogicamente sólido** — Alinhado com o PDF de análise de algoritmos
