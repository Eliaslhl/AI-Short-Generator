"""
config.py – Centralised configuration for AI Shorts Generator.

All tuneable parameters live here so you never have to hunt through
multiple files to change a path, model name, or threshold.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


# ──────────────────────────────────────────────
#  Absolute project paths
# ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent   # repo root
DATA_DIR   = BASE_DIR / "data"
VIDEO_DIR  = DATA_DIR / "videos"
CLIPS_DIR  = DATA_DIR / "clips"
BROLL_DIR  = DATA_DIR / "broll"

# Make sure every directory exists at import time
for _d in (VIDEO_DIR, CLIPS_DIR, BROLL_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
#  Settings (can be overridden via .env file)
# ──────────────────────────────────────────────
class Settings(BaseSettings):
    # ---------- Ollama ----------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str    = "llama3"          # or "mistral"
    ollama_timeout: int  = 60                # seconds

    # ---------- Whisper ----------
    whisper_model: str   = "base"            # tiny | base | small | medium | large
    whisper_device: str  = "cpu"             # cpu | cuda
    whisper_language: str = "en"             # set to "" for auto-detect

    # ---------- Clip selection ----------
    max_clips: int       = 10
    min_clip_duration: int = 15              # seconds
    max_clip_duration: int = 45              # seconds

    # ---------- Video output ----------
    output_width: int    = 1080
    output_height: int   = 1920             # 9:16 portrait
    output_fps: int      = 30
    output_bitrate: str  = "4000k"

    # ---------- spaCy ----------
    spacy_model: str     = "en_core_web_sm"

    # ---------- Paths (as strings for .env compat) ----------
    data_dir:  str = str(DATA_DIR)
    video_dir: str = str(VIDEO_DIR)
    clips_dir: str = str(CLIPS_DIR)
    broll_dir: str = str(BROLL_DIR)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single shared instance
settings = Settings()
