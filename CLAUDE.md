# CLAUDE.md — Projeto Complexidade Algoritmos

Documento de contexto para o assistente. Estado **após refatoração completa** (Fases 0–5 — monorepo com Turborepo).

---

## 1. O que é

Sistema acadêmico (Complexidade de Algoritmos) que recomenda **rotas urbanas multimodais em Recife**, otimizando **tempo, custo, risco** via **Dijkstra** ou **A\*** sobre grafo multimodal.

```
peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm
```

Modais: `walk`, `bike`, `car`, `moto`, `bus`, `uber_car`, `uber_moto`.

---

## 2. Monorepo (Turborepo)

Três workspaces em `apps/`, orquestrados por `turbo.json` + npm workspaces:

| Workspace | Nome | Tecnologia | Função |
|-----------|------|------------|--------|
| `apps/engine` | `@rotas/engine` | Python | Motor de roteamento (Dijkstra/A\*) |
| `apps/api`    | `@rotas/api`    | Python (FastAPI) | API HTTP; importa engine **in-process** |
| `apps/web`    | `@rotas/web`    | Node (React + Vite + Leaflet) | UI |

Comandos raiz:

```bash
npm run dev          # turbo: paralelo (web + api + engine watch)
npm run calc         # roda engine/main.py com input.json
npm run visualize    # gera route_map.html
npm run build        # build do web
```

Per-app: `npm run <task> --workspace=@rotas/<nome>`.

---

## 3. Estrutura

```
.
├── package.json              # workspaces npm
├── turbo.json                # task graph
├── README.md                 # entrada única
├── CLAUDE.md                 # este arquivo
├── .gitignore
│
├── apps/
│   ├── engine/
│   │   ├── package.json      # @rotas/engine (scripts wrappers)
│   │   ├── requirements.txt
│   │   ├── main.py           # CLI fino
│   │   ├── input.json
│   │   ├── core/
│   │   │   ├── config.py       # WEIGHTS, GASOLINE_PRICE, paths absolutos
│   │   │   ├── restrictions.py # parse() -> ModalRestriction
│   │   │   ├── normalization.py# calibrate() Min-Max
│   │   │   └── pipeline.py     # run_route() — PURA
│   │   ├── graph/              # GraphBuilder + módulos focados (geo, osm_loader, multimodal_builder, gtfs_integration, graph_cache, cost_calculator, risk_calculator, normalizer)
│   │   ├── routing/            # MultimodalSearchBase + DijkstraMultimodal + AStarMultimodal (compartilham toda lógica de transição/custo), PathReconstructor
│   │   ├── loaders/            # CSVLoader, WeatherAPI
│   │   ├── scripts/            # visualize_route.py
│   │   ├── data/               # CSVs + GTFS (gitignored)
│   │   ├── cache/              # grafo serializado (gitignored)
│   │   └── output/             # resultados (gitignored, .gitkeep)
│   │
│   ├── api/
│   │   ├── package.json      # @rotas/api (wrapper de uvicorn)
│   │   ├── requirements.txt
│   │   └── app/main.py       # importa core.pipeline via sys.path
│   │
│   └── web/
│       ├── package.json      # @rotas/web
│       ├── vite.config.js
│       ├── index.html
│       └── src/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── ALGORITHMS.md
    └── DATA.md
```

---

## 4. Contrato de `run_route` (motor puro)

```python
# Importável de apps/engine/ (sys.path inclui apps/engine)
from core.pipeline import run_route, RouteError

result = run_route({
    "origem": [-8.062742, -34.8739],
    "destino": [-8.117809, -34.900231],
    "modo_inicial": "walk",
    "algoritmo": "dijkstra",
    "restricao_modal": "bus_com_acesso",
})
# -> {"edges": [...], "segments": [...], "resumo": {...}}
```

- **Sem I/O de arquivo** — quem chama decide se grava `output.json`.
- **Paths absolutos** via `core.config.{DATA_DIR, GTFS_DIR, OUTPUT_FILE, ...}` — funciona com qualquer CWD.
- `RouteError` em caso de input inválido / falha de grafo / rota inexistente.

---

## 5. Restrições de modal (`core.restrictions.parse`)

| `restricao_modal` | `allowed_modes` | `bus_required` | `max_walk_distance_km` | `walk_penalty_factor` |
|-------------------|-----------------|----------------|------------------------|-----------------------|
| `walk`/`bike`/`car`/`moto`/`uber_car`/`uber_moto` | `{aquele}` | False | — | 1.0 |
| `bus` ou `bus_com_acesso` | `{walk, bus}` | **True** | 0.5 | 1.4 |
| `bus_estrito` | `{bus}` | False | — | 1.0 |
| `None` | livre | False | — | 1.0 |

---

## 6. Como o backend chama o engine

`apps/api/app/main.py`:

```python
REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = REPO_ROOT / "apps" / "engine"
sys.path.insert(0, str(ENGINE_ROOT))

from core.pipeline import run_route, RouteError
```

O `subprocess` foi removido. O cache do grafo OSMnx fica em memória entre requisições do uvicorn.

---

## 7. Convenções

- **Idioma:** prints, comentários e campos JSON em português (`origem`, `destino`, `tempo`, `custo`, `risco`, `resumo`).
- **Pesos:** `WEIGHTS` em `core/config.py`.
- **Logging:** pipeline usa `logging.getLogger(__name__)`. CLI configura `level=INFO`; backend silencia naturalmente.
- **Encoding:** `main.py` força UTF-8 só em Windows.
- **Cache:** primeira execução baixa OSM e demora; runs seguintes usam `apps/engine/cache/`.

---

## 8. Histórico das refatorações aplicadas

1. **Fase 0 — Limpeza:** apagados `ex.py`, `temp_output.txt`, `patch_cache_integration.py`; movidos artefatos gerados pra `output/`.
2. **Fase 1 — Docs:** 7 markdowns consolidados em `README.md` + `docs/{ARCHITECTURE,ALGORITHMS,DATA}.md`.
3. **Fase 2 — `core/`:** `main.py` quebrado em `core/{config, restrictions, normalization, pipeline}.py`. Pipeline puro e importável.
4. **Fase 3 — Backend in-process:** removido subprocess; FastAPI chama `run_route` direto.
5. **Fase 4 — Layout final inicial:** `visualize_route.py` → `scripts/`.
6. **Fase 5 — Monorepo Turborepo:** tudo movido para `apps/{engine,api,web}/`; `package.json` raiz com workspaces; `turbo.json` com tarefas (`dev`, `build`, `calc`, `visualize`). Paths Python convertidos para absolutos (`core.config.ENGINE_ROOT` e derivados).

---

## 9. Pendências conhecidas

- Sem testes automatizados (`tests/` ainda não existe).
- Sem tipagem estática (`mypy`).
- `pyproject.toml` ainda não substituiu `requirements.txt`.
- Ambiente atual sem `pandas`/`osmnx`/`turbo` instalados — smoke test ponta-a-ponta precisa rodar localmente.
