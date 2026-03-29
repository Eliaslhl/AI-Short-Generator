#!/bin/sh
set -e

echo "=== Running Alembic migrations ==="
echo "Waiting for database to be reachable (120s timeout) before running migrations..."
python - <<'PY'
import os,sys,time,asyncio
try:
    import asyncpg
except Exception as e:
    print('asyncpg not installed or import failed:', e)
    sys.exit(1)

url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set; aborting')
    sys.exit(1)

deadline = time.time() + 120
while time.time() < deadline:
    try:
        conn = asyncio.get_event_loop().run_until_complete(asyncpg.connect(url, timeout=5))
        asyncio.get_event_loop().run_until_complete(conn.close())
        print('Database reachable')
        break
    except Exception as e:
        print('DB not ready yet, retrying...', str(e))
        time.sleep(2)
else:
    print('Database did not become reachable within 120s; exiting with failure')
    sys.exit(1)

alembic upgrade head || echo "WARNING: Alembic migration failed, continuing anyway..."

echo "=== Starting uvicorn ==="
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}"
