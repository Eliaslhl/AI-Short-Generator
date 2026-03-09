#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  run.sh – Start the AI Shorts Generator server
#  Usage: bash run.sh
# ─────────────────────────────────────────────────────────────
set -e

# Resolve script directory so this works from any cwd
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -d ".venv" ]; then
  echo "❌  .venv not found. Run 'bash setup.sh' first."
  exit 1
fi

source .venv/bin/activate

# Use the venv's uvicorn directly (avoids PATH issues)
UVICORN="$SCRIPT_DIR/.venv/bin/uvicorn"

if [ ! -x "$UVICORN" ]; then
  echo "❌  uvicorn not found in .venv. Run 'bash setup.sh' first."
  exit 1
fi

echo ""
echo "  🚀 Starting AI Shorts Generator…"
echo "  📡 API:  http://localhost:8000/api"
echo "  📖 Docs: http://localhost:8000/docs"
echo "  🌐 React frontend: cd frontend-react && npx vite --port 5173"
echo ""

"$UVICORN" backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend
