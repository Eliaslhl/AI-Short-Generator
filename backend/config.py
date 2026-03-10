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
    # ---------- Database ----------
    database_url: str = "sqlite+aiosqlite:///./data/app.db"   # override with postgresql+asyncpg:// in prod

    # ---------- Ollama ----------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str    = "llama3"          # or "mistral"
    ollama_timeout: int  = 60                # seconds

    # ---------- Groq (free cloud LLM fallback) ----------
    groq_api_key: str    = ""                # set in .env → GROQ_API_KEY
    groq_model: str      = "llama-3.3-70b-versatile"  # free tier model

    # ---------- Whisper ----------
    whisper_model: str   = "base"            # tiny | base | small | medium | large
    whisper_device: str  = "cpu"             # cpu | cuda
    whisper_language: str = ""               # "" = auto-detect (recommended); set "en", "fr"… to force a language

    # ---------- Clip selection ----------
    max_clips: int       = 10
    min_clip_duration: int = 20              # seconds — min to have enough content
    max_clip_duration: int = 60              # seconds — 1 min max for shorts

    # ---------- Video output ----------
    output_width: int    = 1080
    output_height: int   = 1920             # 9:16 portrait
    output_fps: int      = 30
    output_bitrate: str  = "4000k"

    # ---------- spaCy ----------
    spacy_model: str     = "en_core_web_sm"

    # ---------- Stripe ----------
    stripe_secret_key: str                  = ""
    stripe_webhook_secret: str              = ""
    stripe_standard_monthly_price_id: str   = ""
    stripe_standard_yearly_price_id: str    = ""
    stripe_pro_monthly_price_id: str        = ""
    stripe_pro_yearly_price_id: str         = ""
    stripe_proplus_monthly_price_id: str    = ""
    stripe_proplus_yearly_price_id: str     = ""

    # ---------- Paths (as strings for .env compat) ----------
    data_dir:  str = str(DATA_DIR)
    video_dir: str = str(VIDEO_DIR)
    clips_dir: str = str(CLIPS_DIR)
    broll_dir: str = str(BROLL_DIR)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unknown .env vars (auth, mail, stripe…)


# Single shared instance
settings = Settings()
