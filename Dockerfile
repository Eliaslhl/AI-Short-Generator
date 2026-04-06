# ──────────────────────────────────────────────────────────────────────────────
#  AI Shorts Generator – Backend Dockerfile
#  Base: Python 3.11 slim + ffmpeg + system fonts for MoviePy/TextClip
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11-bullseye

# System deps: ffmpeg (video), fonts (MoviePy TextClip), build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    gcc \
    g++ \
    libpq-dev \
    curl \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper tiny model so first request isn't slow
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

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
