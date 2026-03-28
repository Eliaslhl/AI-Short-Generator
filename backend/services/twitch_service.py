"""
twitch_service.py – Download a Twitch clip or VOD using yt-dlp.

Supports both:
- Direct clips: https://www.twitch.tv/{channel}/clip/{clip_name}
- VODs: https://www.twitch.tv/videos/{vod_id}

Returns the local file path and the video title.
"""

import logging
import re
import subprocess
import sys
from pathlib import Path

from backend.config import settings

# Resolve yt-dlp from the same virtual-env
_VENV_BIN = Path(sys.executable).parent
_YTDLP_BIN = _VENV_BIN / "yt-dlp"

logger = logging.getLogger(__name__)


def _validate_twitch_url(url: str) -> bool:
    """Validate that the URL is a valid Twitch clip or VOD URL."""
    url_lower = url.lower().strip()
    
    # Check domain
    if "twitch.tv" not in url_lower:
        return False
    
    # Must be either:
    # 1. A clip URL: twitch.tv/{channel}/clip/{clip_name}
    # 2. A VOD URL: twitch.tv/videos/{vod_id}
    # 3. A VOD URL: twitch.tv/{channel}/videos/{vod_id}
    
    clip_pattern = r'twitch\.tv/\w+/clip/[\w-]+'
    vod_pattern = r'twitch\.tv/videos/\d+'
    vod_channel_pattern = r'twitch\.tv/\w+/videos/\d+'
    
    return bool(
        re.search(clip_pattern, url_lower) or
        re.search(vod_pattern, url_lower) or
        re.search(vod_channel_pattern, url_lower)
    )


def download_video(twitch_url: str, job_id: str) -> tuple[Path, str]:
    """
    Download a Twitch clip or VOD using yt-dlp.
    
    Args:
        twitch_url: Direct URL to a Twitch clip or VOD
        job_id: Job ID for logging and temp file naming
    
    Returns:
        Tuple of (video_path, title)
    
    Raises:
        RuntimeError: If download fails or URL is invalid
    """
    
    # Validate URL
    if not _validate_twitch_url(twitch_url):
        raise RuntimeError(
            "Invalid Twitch URL. Expected format: "
            "https://www.twitch.tv/CHANNEL/clip/CLIP_NAME or "
            "https://www.twitch.tv/videos/VOD_ID"
        )
    
    # Create temp directory for this job
    temp_dir = Path(settings.video_temp_dir) / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Output template for downloaded video
    output_template = temp_dir / "video.%(ext)s"
    
    logger.info(f"[{job_id}] Downloading Twitch video: {twitch_url}")
    
    try:
        # Build yt-dlp command
        cmd = [
            str(_YTDLP_BIN),
            "--quiet",
            "-f", "best[ext=mp4]",  # Prefer MP4 format
            "-o", str(output_template),
            "--no-warnings",
            "--socket-timeout", "60",
            twitch_url,
        ]
        
        logger.debug(f"[{job_id}] Running: {' '.join(cmd)}")
        
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=300,  # 5 minutes
            text=True,
        )
        
        # Find the downloaded file
        video_files = list(temp_dir.glob("video.*"))
        if not video_files:
            raise RuntimeError("No video file found after download")
        
        video_path = video_files[0]
        logger.info(f"[{job_id}] Downloaded to: {video_path}")
        
        # Get video title using ffprobe
        try:
            probe_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=tags",
                "-of", "default=noprint_wrappers=1",
                str(video_path),
            ]
            probe_result = subprocess.run(
                probe_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Try to extract title from tags
            title = "Twitch Clip"
            if "tag:title=" in probe_result.stdout:
                for line in probe_result.stdout.split("\n"):
                    if line.startswith("tag:title="):
                        title = line.replace("tag:title=", "").strip()
                        break
            
            logger.info(f"[{job_id}] Title: {title}")
            return video_path, title
        except Exception as e:
            logger.warning(f"[{job_id}] Could not extract title: {e}")
            return video_path, "Twitch Clip"
    
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Download timeout after 5 minutes: {e}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        if "This video is not available" in error_msg or "is not available in your country" in error_msg:
            raise RuntimeError(f"Video not available: {error_msg}")
        if "HTTP Error 403" in error_msg or "HTTP Error 401" in error_msg:
            raise RuntimeError(f"Access denied (login may be required): {error_msg}")
        if "HTTP Error 404" in error_msg:
            raise RuntimeError(f"Video not found: {error_msg}")
        raise RuntimeError(f"Download failed: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during download: {e}")


def get_cookies_file() -> str | None:
    """
    Get Twitch cookies file path if available.
    
    Currently returns None as Twitch generally doesn't require cookies
    for public clips and VODs. Can be extended in the future.
    """
    return None
