#!/bin/sh
set -e

echo "=== Ensuring Playwright browsers are installed ==="
python -m playwright install chromium 2>/dev/null || echo "WARNING: Playwright chromium install skipped or failed (may auto-install on first use)"

if [ "${MIGRATE_ON_START:-true}" = "true" ]; then
    echo "=== Running Alembic migrations ==="
    alembic upgrade head || echo "WARNING: Alembic migration failed, continuing anyway..."
else
    echo "=== MIGRATE_ON_START is false — skipping Alembic migrations ==="
fi

echo "=== Starting uvicorn ==="
# Some hosts (Railway) may inject a PORT value used for TCP services
# (for example Postgres uses 5432). If PORT is set to 5432, it's almost
# certainly the database port and not intended for the HTTP server. To
# avoid accidentally binding the HTTP server to the DB port (which then
# receives non-HTTP traffic), default to 8000 when PORT is 5432.
_port="${PORT:-8000}"
# If the platform injects PORT=5432 (commonly the Postgres port), avoid
# binding the HTTP server to that port. Use a robust numeric comparison.
if [ "${_port}" = "5432" ] || [ "${_port}" -eq 5432 ] 2>/dev/null; then
    echo "Detected PORT=5432 (Postgres). Overriding to 8000 for HTTP server."
    _port=8000
fi

exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${_port}" \
    --workers "${UVICORN_WORKERS:-1}"
