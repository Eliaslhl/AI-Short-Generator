"""
config.py – Centralised configuration for AI Shorts Generator.

All tuneable parameters live here so you never have to hunt through
multiple files to change a path, model name, or threshold.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
import math
import os

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


# ──────────────────────────────────────────────
#  Absolute project paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = BASE_DIR / "data"
VIDEO_DIR = DATA_DIR / "videos"
CLIPS_DIR = DATA_DIR / "clips"
BROLL_DIR = DATA_DIR / "broll"

# Make sure every directory exists at import time
for _d in (VIDEO_DIR, CLIPS_DIR, BROLL_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
#  Settings (can be overridden via .env file)
# ──────────────────────────────────────────────
class Settings(BaseSettings):
    # ---------- Database ----------
    database_url: str = (
        "sqlite+aiosqlite:///./data/app.db"  # override with postgresql+asyncpg:// in prod
    )

    # ---------- Ollama ----------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"  # or "mistral"
    ollama_timeout: int = 60  # seconds

    # ---------- Groq (free cloud LLM fallback) ----------
    groq_api_key: str = ""  # set in .env → GROQ_API_KEY
    groq_model: str = "llama-3.3-70b-versatile"  # free tier model

    # ---------- Whisper ----------
    whisper_model: str = "base"  # tiny | base | small | medium | large
    whisper_device: str = "cpu"  # cpu | cuda
    whisper_language: str = (
        ""  # "" = auto-detect (recommended); set "en", "fr"… to force a language
    )

    # ---------- Processing / performance tuning ----------
    # When processing a video we download a low-res "processing" copy
    # (height in pixels). This speeds decoding and reduces I/O. Keep
    # the original for final exports if you need full quality.
    processing_max_height: int = 480
    
    # Platform-specific resolutions for optimal quality/speed tradeoffs:
    # - YouTube: high quality (1080p) for crisp shorts
    # - Twitch: lower resolution (360p) to handle huge VODs quickly
    youtube_processing_max_height: int = 1080
    twitch_processing_max_height: int = 360

    # Two-pass transcription: small/faster model for coarse pass, then
    # a larger model (or same) for refined word-timestamps on candidates.
    whisper_fast_model: str = "tiny"
    whisper_refine_model: str = "base"
    # Two-pass transcription tuning
    two_pass_window_size: float = 15.0  # seconds per analysis window
    two_pass_window_overlap: float = 1.0  # seconds overlap between windows
    two_pass_conf_threshold: float = (
        0.70  # below this avg word prob we refine (higher -> more refine)
    )
    two_pass_pad: float = 0.5  # pad seconds around flagged windows
    two_pass_max_refine_fraction: float = (
        0.15  # max fraction of audio seconds to refine (0.15 = 15%)
    )
    # Dynamic cap (seconds) for the refine phase — if the refine phase runs
    # longer than this, we abort submitting new windows. Helps bound latency.
    two_pass_dynamic_cap_seconds: float = 8.0

    # Degree of parallelism for transcription/scoring on CPU-bound workers
    transcribe_workers: int = 4

    # Preferred ffmpeg hardware accel / encoder. Empty = software libx264.
    # Examples: "videotoolbox" (macOS), "nvenc" (NVIDIA). This is used
    # by ffmpeg wrapper calls where available.
    ffmpeg_hwaccel: str = ""

    # ---------- yt-dlp JavaScript challenge solver (EJS) ----------
    # If your environment needs to solve JS challenges (YouTube pages that
    # require a JS runtime), you can configure the preferred runtime and
    # remote component source. Set these via .env in production if needed.
    # Examples:
    #   YTDLP_JS_RUNTIMES=node
    #   YTDLP_REMOTE_COMPONENTS=ejs:npm
    # Leave empty to skip passing these options to yt-dlp.
    ytdlp_js_runtimes: str = "node"
    ytdlp_remote_components: str = "ejs:npm"
    # How to enable yt-dlp JS solver flags. One of:
    #   - "always"       : always pass --js-runtimes / --remote-components
    #   - "when_cookies" : only pass flags when cookies are provided (default)
    #   - "on_error"     : try without flags first, then retry with flags if a
    #                       JS-challenge-related error is detected
    ytdlp_enable_js: str = "when_cookies"

    # Fallback player clients to try when YouTube returns bot-check.
    # Passed as: --extractor-args "youtube:player_client=<value>"
    # Example values: "android,web" or "ios,android,web"
    ytdlp_botcheck_player_clients: str = "android,web"
    # If True, add --impersonate <target> to the first yt-dlp attempt when
    # impersonation support is available in the runtime.
    ytdlp_impersonate_default: bool = False

    # ---------- yt-dlp download tuning (performance) ----------
    # External downloader to use with yt-dlp (e.g. "aria2c"). Leave empty
    # to use yt-dlp internal downloader. Using aria2c (with tuned args)
    # can drastically speed up downloads for fragmented streams.
    ytdlp_downloader: str = ""
    # Arguments to pass to --downloader-args. Example: "aria2c:-x16 -s16 -k1M"
    ytdlp_downloader_args: str = ""
    # If >0, pass --concurrent-fragments N to yt-dlp (useful for HLS/DASH)
    ytdlp_concurrent_fragments: int = 0

    # Optional outbound proxy for yt-dlp (recommended for strict bot-checks
    # on datacenter IPs). Example: http://user:pass@host:port
    ytdlp_proxy_url: str = ""
    # Force IPv4 for yt-dlp requests (can help on some hosts/networks).
    ytdlp_force_ipv4: bool = True
    # Network resilience settings for yt-dlp (especially useful with home proxies)
    ytdlp_socket_timeout: int = 60
    ytdlp_retries: int = 8
    ytdlp_extractor_retries: int = 6
    ytdlp_retry_sleep_seconds: int = 3

    # Timeout (seconds) for yt-dlp subprocess downloads. Increase if you
    # regularly download long VODs or slow streams. Default 3600 (1 hour).
    ytdlp_download_timeout: int = 3600

    # Allow downloading the full VOD (not limited by processing_max_height).
    # When true, the service will request the best available format and use
    # the configured external downloader (aria2c) for speed. Default: False.
    ytdlp_allow_full_vod: bool = False

    # Number of fragment retries for yt-dlp when downloading segmented HLS
    # streams. Increase if your network is flaky. Default: 5
    ytdlp_fragment_retries: int = 5

    # ---------- Clip selection ----------
    max_clips: int = 10
    min_clip_duration: int = 20  # seconds — min to have enough content
    max_clip_duration: int = 60  # seconds — 1 min max for shorts

    # ---------- Video output ----------
    output_width: int = 1080
    output_height: int = 1920  # 9:16 portrait
    output_fps: int = 30
    # Video bitrate for default/fast exports. Set to 10000k (≈10 Mbps) which
    # is a good target for Instagram Reels / TikTok uploads — export slightly
    # above the platform compression.
    output_bitrate: str = "10000k"
    # Render quality presets: "default", "hq1080", "hq4k"
    render_quality: str = "hq1080"
    # High quality presets (tunable)
    # High-quality 1080p target bitrate (used for HQ profile and hardware encoders)
    hq1080_bitrate: str = "18000k"
    hq4k_bitrate: str = "20000k"
    hq_crf: int = 16
    hq_preset: str = "slower"

    # Audio export preferences
    output_audio_bitrate: str = "320k"
    output_audio_samplerate: int = 44100

    # ---------- Rendering / parallelism ----------
    # If None, compute a sane default based on CPU cores: min(4, floor(0.75 * logical_cpus)).
    # This prevents overloading small machines while giving good throughput on larger hosts.
    render_workers: Optional[int] = None

    # ---------- spaCy ----------
    spacy_model: str = "en_core_web_sm"

    # ---------- Stripe ----------
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_standard_monthly_price_id: str = ""
    stripe_standard_yearly_price_id: str = ""
    stripe_pro_monthly_price_id: str = ""
    stripe_pro_yearly_price_id: str = ""
    stripe_proplus_monthly_price_id: str = ""
    stripe_proplus_yearly_price_id: str = ""

    # ---------- Paths (as strings for .env compat) ----------
    data_dir: str = str(DATA_DIR)
    video_dir: str = str(VIDEO_DIR)
    clips_dir: str = str(CLIPS_DIR)
    broll_dir: str = str(BROLL_DIR)
    # Temporary working directory for downloads / processing (can be overridden via VIDEO_TEMP_DIR)
    video_temp_dir: str = str(DATA_DIR / "tmp")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unknown .env vars (auth, mail, stripe…)


# Single shared instance
settings = Settings()


def get_render_workers() -> int:
    """Return the effective number of render workers.

    Uses settings.render_workers if set, otherwise computes a sensible default.
    """
    if settings.render_workers is not None:
        return max(1, int(settings.render_workers))

    # try psutil first (more reliable in virtual envs), fallback to os.cpu_count()
    cores = None
    try:
        if psutil is not None:
            cores = psutil.cpu_count(logical=True)
    except Exception:
        cores = None

    if not cores:
        cores = os.cpu_count() or 4

    # compute 75% of logical cores, min 1, cap at 4 for conservative default
    val = max(1, min(4, math.floor(0.75 * cores)))
    return int(val)
