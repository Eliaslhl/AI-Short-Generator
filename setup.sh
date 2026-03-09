#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  setup.sh – One-time environment setup for AI Shorts Generator
#  Requires Python 3.11  (spaCy/blis not yet compatible with 3.13)
#  Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────
set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       AI Shorts Generator – Setup Script         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Locate Python 3.11 ───────────────────────────────────
# spaCy (via blis/thinc) does NOT yet support Python 3.13.
# We need 3.11 explicitly.
info "Looking for Python 3.11…"

PYTHON311=""
for candidate in \
    /opt/homebrew/opt/python@3.11/bin/python3.11 \
    /usr/local/opt/python@3.11/bin/python3.11 \
    /usr/local/bin/python3.11 \
    $(command -v python3.11 2>/dev/null || true); do
  if [ -x "$candidate" ]; then
    PYTHON311="$candidate"
    break
  fi
done

if [ -z "$PYTHON311" ]; then
  warn "Python 3.11 not found. Attempting to install via Homebrew…"
  if command -v brew &>/dev/null; then
    brew install python@3.11
    PYTHON311=/opt/homebrew/opt/python@3.11/bin/python3.11
  else
    error "Python 3.11 is required.\nInstall it: brew install python@3.11"
  fi
fi

PY_VER=$("$PYTHON311" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
success "Using Python $PY_VER → $PYTHON311"

# ── 2. (Re)create virtual environment with Python 3.11 ──────
if [ -d ".venv" ]; then
  VENV_PY=$(.venv/bin/python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
  if [ "$VENV_PY" != "3.11" ]; then
    warn "Existing .venv uses Python $VENV_PY, not 3.11. Recreating…"
    rm -rf .venv
  else
    warn ".venv already exists with Python 3.11 – skipping creation."
  fi
fi

if [ ! -d ".venv" ]; then
  info "Creating virtual environment with Python 3.11…"
  "$PYTHON311" -m venv .venv
  success "Virtual environment created."
fi

# Activate venv
source .venv/bin/activate
success "Virtual environment activated."

# ── 3. Install Python dependencies ──────────────────────────
info "Upgrading pip…"
pip install --upgrade pip --quiet

info "Installing Python packages from requirements.txt…"
pip install -r requirements.txt
success "Python packages installed."

# ── 4. Download spaCy language model ────────────────────────
info "Downloading spaCy English model (en_core_web_sm)…"
python -m spacy download en_core_web_sm --quiet
success "spaCy model ready."

# ── 5. Check ffmpeg ──────────────────────────────────────────
info "Checking ffmpeg…"
if command -v ffmpeg &>/dev/null; then
  FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
  success "ffmpeg found: $FFMPEG_VER"
else
  warn "ffmpeg not found."
  echo "  Install: brew install ffmpeg"
fi

# ── 6. Check yt-dlp ──────────────────────────────────────────
info "Checking yt-dlp…"
if python -c "import yt_dlp" 2>/dev/null; then
  success "yt-dlp is available."
else
  warn "yt-dlp import failed."
fi

# ── 7. Check Ollama ──────────────────────────────────────────
info "Checking Ollama…"
if command -v ollama &>/dev/null; then
  success "Ollama CLI found. Pull a model: ollama pull llama3"
else
  warn "Ollama not found (optional). Install: https://ollama.com"
  echo "  The app uses a rule-based fallback without Ollama."
fi

# ── 8. Create .env if missing ────────────────────────────────
if [ ! -f ".env" ]; then
  info "Creating default .env file…"
  cat > .env <<'EOF'
# AI Shorts Generator – Environment Variables
# Uncomment and edit to override defaults from config.py

# OLLAMA_MODEL=llama3
# OLLAMA_BASE_URL=http://localhost:11434

# WHISPER_MODEL=base
# WHISPER_DEVICE=cpu
# WHISPER_LANGUAGE=en

# MAX_CLIPS=10
# MIN_CLIP_DURATION=15
# MAX_CLIP_DURATION=45
EOF
  success ".env file created."
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅  Setup complete!                             ║"
echo "║                                                  ║"
echo "║  Start the server:  bash run.sh                  ║"
echo "║  Open browser:      http://localhost:8000        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       AI Shorts Generator – Setup Script         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Python version check ─────────────────────────────────
info "Checking Python version…"
PYTHON=$(command -v python3 || command -v python || error "Python not found. Install Python 3.9+.")
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Found Python $PY_VER"
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)"; then
  success "Python version OK"
else
  error "Python 3.9+ is required. Current: $PY_VER"
fi

# ── 2. Create virtual environment ───────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating virtual environment (.venv)…"
  $PYTHON -m venv .venv
  success "Virtual environment created."
else
  warn ".venv already exists – skipping creation."
fi

# Activate venv
source .venv/bin/activate

# ── 3. Install Python dependencies ──────────────────────────
info "Installing Python packages from requirements.txt…"
pip install --upgrade pip --quiet
pip install -r requirements.txt
success "Python packages installed."

# ── 4. Download spaCy language model ────────────────────────
info "Downloading spaCy English model (en_core_web_sm)…"
python -m spacy download en_core_web_sm --quiet
success "spaCy model ready."

# ── 5. Check ffmpeg ──────────────────────────────────────────
info "Checking ffmpeg…"
if command -v ffmpeg &> /dev/null; then
  FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
  success "ffmpeg found: $FFMPEG_VER"
else
  warn "ffmpeg not found."
  echo ""
  echo "  Install ffmpeg:"
  echo "    macOS:   brew install ffmpeg"
  echo "    Ubuntu:  sudo apt install ffmpeg"
  echo "    Windows: https://ffmpeg.org/download.html"
  echo ""
fi

# ── 6. Check yt-dlp ──────────────────────────────────────────
info "Checking yt-dlp…"
if python -c "import yt_dlp" 2>/dev/null; then
  success "yt-dlp is available."
else
  warn "yt-dlp not importable – re-run pip install."
fi

# ── 7. Check Ollama ──────────────────────────────────────────
info "Checking Ollama…"
if command -v ollama &> /dev/null; then
  success "Ollama CLI found."
  echo ""
  echo "  Make sure to pull a model before running:"
  echo "    ollama pull llama3"
  echo "    ollama pull mistral"
  echo ""
else
  warn "Ollama not found."
  echo ""
  echo "  Install Ollama from: https://ollama.com"
  echo "  Then run: ollama pull llama3"
  echo ""
  echo "  ⚠  The app will still work without Ollama."
  echo "     It uses a rule-based hook generator as fallback."
  echo ""
fi

# ── 8. Create .env if missing ────────────────────────────────
if [ ! -f ".env" ]; then
  info "Creating default .env file…"
  cat > .env <<'EOF'
# AI Shorts Generator – Environment Variables
# Uncomment and edit to override defaults from config.py

# OLLAMA_MODEL=llama3
# OLLAMA_BASE_URL=http://localhost:11434

# WHISPER_MODEL=base
# WHISPER_DEVICE=cpu
# WHISPER_LANGUAGE=en

# MAX_CLIPS=10
# MIN_CLIP_DURATION=15
# MAX_CLIP_DURATION=45
EOF
  success ".env file created."
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅  Setup complete!                             ║"
echo "║                                                  ║"
echo "║  Start the server:                               ║"
echo "║    bash run.sh                                   ║"
echo "║                                                  ║"
echo "║  Then open: http://localhost:8000                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
