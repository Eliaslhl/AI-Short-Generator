# ──────────────────────────────────────────────────────────────────────────────
#  AI Shorts Generator – Backend Dockerfile
#  Base: Python 3.11 slim + ffmpeg + system fonts for MoviePy/TextClip
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11-bullseye

# System deps: keep only runtime essentials for faster/more reliable Railway builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: pre-download Whisper tiny model during build.
# Disabled by default to avoid build failures/timeouts on constrained CI builders.
ARG PRELOAD_WHISPER=0
RUN if [ "$PRELOAD_WHISPER" = "1" ]; then \
            python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"; \
        else \
            echo "Skipping Whisper pre-download (PRELOAD_WHISPER=$PRELOAD_WHISPER)"; \
        fi

# Copy application code
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create data directories (clips, videos)
RUN mkdir -p data/clips data/videos

# Copy and prepare startup script
COPY start.sh .
RUN chmod +x start.sh

# Copy YouTube refresher script
COPY scripts/refresh_youtube_cookies.py /app/scripts/

# Port exposed by Railway
EXPOSE 8000

# Start via script (handles alembic + uvicorn cleanly)
CMD ["./start.sh"]
