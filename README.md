# Motor de Rotas Multimodais — Recife (Backend)

Backend de um aplicativo de navegação (estilo Waze/Moovit) focado na Região
Metropolitana do Recife. Calcula **rotas multimodais** (caminhada, bicicleta,
carro, moto, ônibus, Uber) combinando malha viária com dados de transporte
público (GTFS), aplicando **pesos dinâmicos** nas arestas do grafo a partir de
fatores externos (velocidade do modal, crime, acidentes, alagamento, clima,
maré).

Projeto da disciplina de **Complexidade de Algoritmos**. Os algoritmos de
roteamento (**A\*** para malha contínua e **Dijkstra** para a rede GTFS) são
implementados na camada `services/`. Esta etapa entrega o *scaffold*: estrutura
de pastas, entities do PostgreSQL, schemas de I/O tipados e o endpoint
`POST /api/calculate` retornando um mock com o formato exato de saída.

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
  graph/         construção do grafo + cálculo de risco/custo (stubs)
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

> A API sobe sem dados (o schema é criado pelas migrações; os pesos têm fallback
> neutro). Para popular os fatores e a rede de ônibus, restaure os dumps SQL na
> ordem abaixo (ver [dumps/README.md](dumps/README.md)):
>
> ```bash
> docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_factors.sql
> docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_gtfs.sql
> # bus_stop_times (necessário para roteamento walk + bus), comprimido:
> gunzip -c dumps/seed_stop_times.sql.gz | docker exec -i rotas_recife_db psql -U rotas -d rotas_recife
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
