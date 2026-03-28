#!/bin/bash
# start_backend.sh - Launch backend server with proper reload settings

cd /Users/elias/Documents/projet/VideoToShortFree/ai-shorts-generator

# Kill any existing processes
pkill -f uvicorn 2>/dev/null

# Start backend
.venv/bin/python -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir backend \
  --reload-delay 2
