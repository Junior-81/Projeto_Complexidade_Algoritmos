# Motor de Rotas Multimodais — Recife (Backend)

Backend de um aplicativo de navegação (estilo Waze/Moovit) focado na Região
Metropolitana do Recife. Calcula **rotas multimodais** (caminhada, bicicleta,
carro, moto, ônibus, Uber) combinando malha viária com dados de transporte
público (GTFS), aplicando **pesos dinâmicos** nas arestas do grafo a partir de
fatores externos (velocidade do modal, crime, acidentes, alagamento, clima,
maré).

Projeto da disciplina de **Complexidade de Algoritmos**. Os algoritmos de
roteamento estão implementados na camada `services/`: **A\*** (com heurística de
Haversine) para as pernas em modal contínuo e **Dijkstra** para a rede de ônibus.
O grafo é montado **por proximidade espacial** a partir das coordenadas reais das
~7.000 paradas do GTFS do Grande Recife — o dump não traz malha viária (OSM) nem
`stop_times`, então a topologia vem das paradas e os **pesos vêm do banco**:
velocidade do modal (`transport_speed`), risco de crime/acidente
(`crime_rate`/`accident_rate`, 50/50) e custo de combustível/Uber/ônibus
(`fuel_consumption`/`uber_price_ranges`). O endpoint `POST /api/calculate`
retorna a rota multimodal real (acesso → ônibus → caminhada) com
`edges`/`segments`/`summary`/`routePoints`. Se o banco estiver indisponível, o
serviço degrada para um grafo sintético de contingência e pesos default, sem 500.

## Stack

- Python 3.12+ · **FastAPI** · **SQLModel** (SQLAlchemy + Pydantic)
- **PostgreSQL** · **Alembic** (migrações) · `uv` (gerenciador de pacotes)
- **Docker / Docker Compose** (forma recomendada de execução)

## Arquitetura

```
app/
  controllers/   rotas FastAPI (camada HTTP)
  services/      lógica de negócio, roteamento (A*/Dijkstra), pesos dinâmicos
  entities/      modelos SQLModel (banco) + schemas Pydantic (I/O)
  loaders/       ingestão dos CSV -> PostgreSQL
  graph/         construção do grafo (proximidade) + cálculo de risco/custo + geo
deploy/          Dockerfile, docker-compose.yml e entrypoint do container
```

## Como rodar (Docker — recomendado)

Sobe **API + PostgreSQL** juntos. As migrações rodam automaticamente no start do
container (ver `deploy/docker-entrypoint.sh`).

```bash
# Da raiz do projeto:
docker compose -f deploy/docker-compose.yml up -d --build
```

- API: `http://localhost:8000` · docs interativas em `http://localhost:8000/docs`
- PostgreSQL exposto no host em `localhost:5433`

```bash
# Acompanhar logs / parar
docker compose -f deploy/docker-compose.yml logs -f api
docker compose -f deploy/docker-compose.yml down
```

> A API sobe sem dados (o schema é criado pelas migrações; o cálculo retorna mock
> e os pesos têm fallback neutro). Para popular os fatores e a rede GTFS, restaure
> os dumps SQL (ver [dumps/README.md](dumps/README.md)):
>
> ```bash
> docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_factors.sql
> docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_gtfs.sql
> ```

## Desenvolvimento local (sem container da API)

Alternativa para iterar com hot-reload, usando o Docker só para o banco:

```bash
# 1. Instalar dependências
uv sync

# 2. Subir só o PostgreSQL
docker compose -f deploy/docker-compose.yml up -d postgres

# 3. Variáveis de ambiente
cp .env.example .env

# 4. Criar o schema (migrações)
uv run alembic upgrade head

# 5. Carregar os fatores (CSV -> banco) — ou restaurar os dumps (ver acima)
uv run load-data

# 6. Rodar a API com reload
uv run uvicorn app.main:app --reload
```

## Endpoint

`POST /api/calculate` — contrato em inglês + camelCase.

```json
{
  "origin": [-8.062742, -34.8739],
  "destination": [-8.117809, -34.900231],
  "initialMode": "walk"
}
```

`initialMode` aceita: `walk`, `bike`, `car`, `moto`, `bus`, `uber_car`, `uber_moto`.

Retorna `edges` (micro-segmentos rua a rua), `segments` (agrupados por modal),
`summary` (totais da viagem) e `routePoints` (sequência de coordenadas para
plotagem no mapa).

## Testes

```bash
uv run pytest
```

## Dados

Os fatores de peso e o feed GTFS do Grande Recife ficam em `data/data/`
(`transport_speed.csv`, `crime_rate.csv`, `accident_rate.csv`,
`fuel_consumption.csv`, `uber_price_ranges.csv`, `weather_factors.csv`,
`tide_factors.csv`, `flood_risk_streets.csv` e `bus_gtfs/`).
