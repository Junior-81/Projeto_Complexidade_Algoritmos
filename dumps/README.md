# Dumps SQL — dados para o banco

Dumps **data-only** (somente dados, formato `COPY`) gerados a partir do banco
populado. São uma alternativa ao loader em Python (`uv run load-data`): você cria
o schema com as migrações e injeta os dados direto, sem precisar dos CSVs.

| Arquivo | Conteúdo | Tabelas |
|---|---|---|
| `seed_factors.sql` | Fatores de peso/risco/custo (núcleo do algoritmo) | `transport_speed`, `crime_rate`, `accident_rate`, `fuel_consumption`, `uber_price_ranges`, `weather_factors`, `tide_factors`, `flood_risk_streets` |
| `seed_gtfs.sql` | Rede de ônibus GTFS (leve) | `bus_routes` (392), `bus_stops` (7.133), `bus_trips` (87.354) |

> O `stop_times.txt` (~3,1M linhas) **não** está incluído: não é carregado nesta
> fase nem usado pelo cálculo atual (tabela `bus_stop_times` fica vazia).

## Como restaurar

Os dumps são **data-only**, então as tabelas precisam existir antes. O schema é
criado pelas migrações Alembic:

```bash
# 1. Banco no ar e schema criado
docker-compose up -d
uv run alembic upgrade head

# 2. Restaurar os dados (banco recém-migrado / tabelas vazias)
docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_factors.sql
docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_gtfs.sql
```

Cliente `psql` instalado localmente? Use direto:

```bash
psql "postgresql://rotas:rotas@localhost:5433/rotas_recife" -f dumps/seed_factors.sql
psql "postgresql://rotas:rotas@localhost:5433/rotas_recife" -f dumps/seed_gtfs.sql
```

## Regenerar os dumps

A partir de um banco já populado (via `uv run load-data`):

```bash
docker exec rotas_recife_db pg_dump -U rotas -d rotas_recife \
  --data-only --no-owner --disable-triggers \
  -t transport_speed -t crime_rate -t accident_rate -t fuel_consumption \
  -t uber_price_ranges -t weather_factors -t tide_factors -t flood_risk_streets \
  > dumps/seed_factors.sql

docker exec rotas_recife_db pg_dump -U rotas -d rotas_recife \
  --data-only --no-owner --disable-triggers \
  -t bus_routes -t bus_stops -t bus_trips \
  > dumps/seed_gtfs.sql
```
