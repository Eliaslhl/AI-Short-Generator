#!/bin/bash

# 🚀 Start Advanced Twitch Processing System
# Usage: ./start_services.sh [rq|celery]

set -e

QUEUE_BACKEND=${1:-rq}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
BACKEND_DIR="${PROJECT_ROOT}/backend"

echo "🎯 Starting VideoToShort Advanced Twitch Processing System"
echo "📦 Queue Backend: ${QUEUE_BACKEND}"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Redis is running
echo -e "${BLUE}[1/4]${NC} Checking Redis..."
if ! command -v redis-server &> /dev/null; then
    echo -e "${RED}❌ Redis not installed${NC}"
    echo "   Install: brew install redis"
    exit 1
fi

if ! redis-cli ping &> /dev/null; then
    echo -e "${YELLOW}⚠️  Redis not running, starting...${NC}"
    redis-server --daemonize yes --logfile /tmp/redis.log
    sleep 1
fi

if redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✅ Redis running (localhost:6379)${NC}"
else
    echo -e "${RED}❌ Failed to start Redis${NC}"
    exit 1
fi

# Check Python and venv
echo ""
echo -e "${BLUE}[2/4]${NC} Checking Python environment..."
if [ ! -d "${BACKEND_DIR}/venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found, creating...${NC}"
    cd "${BACKEND_DIR}"
    python3 -m venv venv
fi

source "${BACKEND_DIR}/venv/bin/activate"
echo -e "${GREEN}✅ Python venv activated${NC}"

# Install/update dependencies
echo ""
echo -e "${BLUE}[3/4]${NC} Installing dependencies..."
cd "${BACKEND_DIR}"
pip install -q -r requirements.txt 2>/dev/null || echo "⚠️  Some packages may not install (optional)"
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create .env if not exists
echo ""
echo -e "${BLUE}[4/4]${NC} Checking configuration..."
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    echo -e "${YELLOW}⚠️  .env not found, creating with defaults...${NC}"
    cat > "${BACKEND_DIR}/.env" << EOF
# Queue Configuration
QUEUE_BACKEND=${QUEUE_BACKEND}
REDIS_URL=redis://localhost:6379/0

# Processing Configuration
CHUNK_DURATION=1800
WINDOW_SIZE=15
WINDOW_OVERLAP=0.5

# Scoring Configuration
AUDIO_WEIGHT=0.5
MOTION_WEIGHT=0.2
TEXT_WEIGHT=0.3
MIN_SCORE_THRESHOLD=0.3
MERGE_THRESHOLD=2.0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
EOF
    echo -e "${GREEN}✅ .env created with defaults${NC}"
fi

# Final checklist
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ All checks passed! Ready to start services${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1️⃣  Start Worker (in terminal 1):"
if [ "${QUEUE_BACKEND}" = "rq" ]; then
    echo -e "   ${BLUE}rq worker${NC}"
else
    echo -e "   ${BLUE}celery -A backend.queue.worker worker --loglevel=info${NC}"
fi
echo ""
echo "2️⃣  Start FastAPI (in terminal 2):"
echo -e "   ${BLUE}cd ${BACKEND_DIR}${NC}"
echo -e "   ${BLUE}uvicorn main:app --reload${NC}"
echo ""
echo "3️⃣  Test API (in terminal 3):"
echo -e "   ${BLUE}curl -X POST http://localhost:8000/api/generate/twitch/advanced -H 'Content-Type: application/json' -d '{\"url\": \"https://www.twitch.tv/videos/123456789\", \"max_clips\": 5, \"language\": \"en\"}'${NC}"
echo ""
echo -e "${YELLOW}Configuration file: ${BACKEND_DIR}/.env${NC}"
echo -e "${YELLOW}Queue backend: ${QUEUE_BACKEND}${NC}"
echo ""
