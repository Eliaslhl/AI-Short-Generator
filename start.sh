#!/bin/sh
set -e

if [ "${MIGRATE_ON_START:-true}" = "true" ]; then
    echo "=== Running Alembic migrations ==="
    alembic upgrade head || echo "WARNING: Alembic migration failed, continuing anyway..."
else
    echo "=== MIGRATE_ON_START is false — skipping Alembic migrations ==="
fi

echo "=== Starting uvicorn ==="
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}"
