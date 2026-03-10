# ──────────────────────────────────────────────────────────────────────────────
#  AI Shorts Generator – Backend Dockerfile
#  Base: Python 3.11 slim + ffmpeg + system fonts for MoviePy/TextClip
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

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

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Pre-download Whisper tiny model so first request isn't slow
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

# Copy application code
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create data directories (clips, videos)
RUN mkdir -p data/clips data/videos

# Port exposed by Railway
EXPOSE 8000

# Run Alembic migrations then start uvicorn
CMD alembic upgrade head && \
    uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers ${UVICORN_WORKERS:-2}
