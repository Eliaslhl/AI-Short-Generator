"""
youtube_service.py – Download a YouTube video using yt-dlp.

Returns the local file path and the video title.
"""

import logging
import re
import subprocess
import sys
from pathlib import Path

from backend.config import settings

# Resolve yt-dlp from the same virtual-env that runs this server,
# so we don't rely on yt-dlp being on the system PATH.
_VENV_BIN = Path(sys.executable).parent
_YTDLP_BIN = _VENV_BIN / "yt-dlp"

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Remove characters that are unsafe in file names."""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def download_video(youtube_url: str, job_id: str) -> tuple[Path, str]:
    """
    Download a YouTube video to data/videos/<job_id>/.

    Parameters
    ----------
    youtube_url : str
        Full YouTube URL (e.g. https://www.youtube.com/watch?v=…)
    job_id : str
        Unique job identifier used to namespace the output directory.

    Returns
    -------
    (video_path, video_title) : tuple[Path, str]
        Absolute path to the downloaded MP4 file and the video title.
    """
    out_dir = Path(settings.video_dir) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── yt-dlp options ──────────────────────────────────────────────────────
    # We ask for the best combined mp4 up to 1080p to keep file sizes sane.
    output_template = str(out_dir / "%(title)s.%(ext)s")

    cmd = [
        str(_YTDLP_BIN),
        # Accept any format — yt-dlp picks the best available and converts to mp4
        "--format", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--output",   output_template,
        "--no-playlist",
        "--no-warnings",
        # tv_embedded bypasses the "Sign in to confirm you're not a bot" check
        # without needing cookies — works for most public videos
        "--extractor-args", "youtube:player_client=tv_embedded,ios,web",
        "--print", "after_move:filepath",
        youtube_url,
    ]

    logger.info(f"Running yt-dlp for job {job_id}: {youtube_url}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp stderr: {e.stderr}")
        logger.error(f"yt-dlp stdout: {e.stdout}")
        raise RuntimeError(f"yt-dlp failed (exit {e.returncode}): {e.stderr.strip() or e.stdout.strip()}")

    # The last non-empty line is the final file path (from --print after_move:filepath)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("yt-dlp produced no output – download may have failed.")

    video_path = Path(lines[-1])

    if not video_path.exists():
        # Fallback: find the first mp4 in the output directory
        mp4_files = list(out_dir.glob("*.mp4"))
        if not mp4_files:
            raise FileNotFoundError(f"No MP4 found in {out_dir} after yt-dlp run.")
        video_path = mp4_files[0]

    video_title = video_path.stem
    logger.info(f"Download complete: {video_path}")
    return video_path, video_title
