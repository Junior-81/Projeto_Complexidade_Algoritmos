# Dumps SQL — dados para o banco

Dumps **data-only** (somente dados, formato `COPY`) gerados a partir do banco
populado. São uma alternativa ao loader em Python (`uv run load-data`): você cria
o schema com as migrações e injeta os dados direto, sem precisar dos CSVs.

| Arquivo | Conteúdo | Tabelas |
|---|---|---|
| `seed_factors.sql` | Fatores de peso/risco/custo (núcleo do algoritmo) | `transport_speed`, `crime_rate`, `accident_rate`, `fuel_consumption`, `uber_price_ranges`, `weather_factors`, `tide_factors`, `flood_risk_streets` |
| `seed_gtfs.sql` | Rede de ônibus GTFS (leve) | `bus_routes` (392), `bus_stops` (7.133), `bus_trips` (87.354) |
| `seed_stop_times.sql.gz` | Sequência de paradas por viagem (**gzip**, ~38 MB) | `bus_stop_times` (3.109.615) |

> **`bus_stop_times` é obrigatória para o roteamento de ônibus** (walk + bus): é
> ela que liga cada viagem à ordem das paradas. Sem ela, o grafo fica só de ruas
> e os modais `walk`/`bus` caem em rota a pé. Por ter ~3,1M linhas (~207 MB cru),
> vai **comprimida** em `.gz` para caber no limite de 100 MB do GitHub.

## Como restaurar

Os dumps são **data-only**, então as tabelas precisam existir antes. O schema é
criado pelas migrações Alembic. Restaure na ordem (FK: `bus_stop_times` depende
de `bus_trips`/`bus_stops`):

```bash
# 1. Banco no ar e schema criado
docker compose -f deploy/docker-compose.yml up -d postgres
uv run alembic upgrade head

# 2. Fatores + rede GTFS leve
docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_factors.sql
docker exec -i rotas_recife_db psql -U rotas -d rotas_recife < dumps/seed_gtfs.sql

# 3. Sequência de paradas (descomprime no pipe; ~3,1M linhas, ~1 min)
gunzip -c dumps/seed_stop_times.sql.gz | docker exec -i rotas_recife_db psql -U rotas -d rotas_recife
```

Cliente `psql` instalado localmente? Use direto:

```bash
psql "postgresql://rotas:rotas@localhost:5433/rotas_recife" -f dumps/seed_factors.sql
psql "postgresql://rotas:rotas@localhost:5433/rotas_recife" -f dumps/seed_gtfs.sql
gunzip -c dumps/seed_stop_times.sql.gz | psql "postgresql://rotas:rotas@localhost:5433/rotas_recife"
```

> Após carregar `bus_stop_times`, o motor reconstrói o grafo na primeira chamada
> de `/api/calculate` (inclui as arestas de ônibus). Se já havia um grafo em
> cache antigo, o nome versionado do cache (`multimodal_graph_busv2.pkl`) garante
> rebuild automático.

## Regenerar os dumps

A partir de um banco já populado:

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

# stop_times comprimido (3,1M linhas)
docker exec rotas_recife_db pg_dump -U rotas -d rotas_recife \
  --data-only --no-owner --disable-triggers \
  -t bus_stop_times | gzip > dumps/seed_stop_times.sql.gz
```

## Notas de correção

- **`fuel_consumption.bike`**: `fixed_cost_per_km` estava em `7` (≈ preço da
  gasolina), o que dava ~R$ 70 numa viagem de 10 km de bicicleta. Corrigido para
  `0` (a bike não tem custo de combustível/tarifa; o esforço físico já é tratado
  à parte no cálculo).
