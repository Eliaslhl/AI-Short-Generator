#!/bin/sh
set -e

echo "=== Running Alembic migrations ==="
alembic upgrade head || echo "WARNING: Alembic migration failed, continuing anyway..."

echo "=== Starting uvicorn ==="
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}"
