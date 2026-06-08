#!/usr/bin/env bash

set -e

echo "[entrypoint] aplicando migrations (alembic upgrade head)..."
for tentativa in 1 2 3 4 5; do
  if alembic upgrade head; then
    break
  fi
  echo "[entrypoint] migration falhou (tentativa $tentativa). Aguardando o banco..."
  sleep 3
done

echo "[entrypoint] iniciando: $*"
exec "$@"
