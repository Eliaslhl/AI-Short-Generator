"""
youtube_service.py – Download a YouTube video using yt-dlp.

Returns the local file path and the video title.
"""

import base64
import logging
import os
import re
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from backend.config import settings

# Resolve yt-dlp from the same virtual-env that runs this server,
# so we don't rely on yt-dlp being on the system PATH.
_VENV_BIN = Path(sys.executable).parent
_YTDLP_BIN = _VENV_BIN / "yt-dlp"

logger = logging.getLogger(__name__)


def _write_cookies_file() -> str | None:
    """
    Decode the YOUTUBE_COOKIES_B64 env var and write to a temp file.
    Returns the path to the cookie file, or None if not configured.
    """
    # Primary single-variable form (preferred)
    b64 = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()

    # Support Rails-like platforms that limit env var size by allowing the
    # cookie file to be split across multiple smaller env vars named
    # YOUTUBE_COOKIES_B64_PART_1, YOUTUBE_COOKIES_B64_PART_2, ...
    if not b64:
        parts = []
        for k, v in os.environ.items():
            if k.startswith("YOUTUBE_COOKIES_B64_PART_"):
                # capture numeric suffix for ordering; fallback to key order
                try:
                    idx = int(k.rsplit("_", 1)[1])
                except Exception:
                    idx = None
                parts.append((idx, k, v))

        if parts:
            # sort by numeric suffix when available, then by key name
            parts.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else t[1]))
            # Sanitize parts: remove accidental surrounding quotes and whitespace
            sanitized_parts = []
            for _, key, val in parts:
                v = val.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                # remove common prefixes (in case someone pasted "base64:" prefix)
                if v.lower().startswith("base64:"):
                    v = v.split("base64:", 1)[1]
                sanitized_parts.append(v)

            b64 = "".join(sanitized_parts)

            # Detect likely-mistake: storing hex hashes instead of raw base64 parts
            # If the concatenated value contains only hex chars and is reasonably long,
            # it's very likely the user pasted SHA256 parts (wrong). Fail early with a clear log.
            if re.fullmatch(r"[0-9a-fA-F]+", b64) and len(b64) >= 64:
                logger.warning(
                    "YOUTUBE_COOKIES_B64_PART_* appear to contain hex hashes rather than base64 data. "
                    "Ensure you paste the raw base64-encoded cookies (not SHA256 of the parts)."
                )
                return None

    if not b64:
        return None
    try:
        content = base64.b64decode(b64).decode("utf-8")
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="yt_cookies_"
        )
        tmp.write(content)
        tmp.flush()
        tmp.close()
        logger.info(f"YouTube cookies written to {tmp.name}")
        # Optional debug: log size and sha256 of the reconstructed cookies file
        # without revealing the contents. Enable by setting YOUTUBE_COOKIES_DEBUG=true
        try:
            if os.environ.get("YOUTUBE_COOKIES_DEBUG", "").lower() in ("1", "true", "yes"):
                size = os.path.getsize(tmp.name)
                with open(tmp.name, "rb") as fh:
                    sha = hashlib.sha256(fh.read()).hexdigest()
                logger.info(f"[YTC DEBUG] cookies file size={size} sha256={sha}")
        except Exception:
            # Do not fail cookie writing for debug logging failures
            pass
        return tmp.name
    except Exception as exc:
        logger.warning(f"Could not decode YOUTUBE_COOKIES_B64: {exc}")
        return None


def _get_cookies_file() -> tuple[str | None, bool]:
    """
    Determine cookies file to use.

    Returns a tuple (path_or_none, is_temp). If the caller set
    YOUTUBE_COOKIES_FILE and the path exists, it will be returned with
    is_temp=False. Otherwise fall back to decoding YOUTUBE_COOKIES_B64 and
    return a temp file path with is_temp=True. If no cookies configured,
    returns (None, False).
    """
    # 1) explicit file path (preferred)
    path = os.environ.get("YOUTUBE_COOKIES_FILE", "").strip()
    if path:
        if os.path.exists(path):
            logger.info(f"Using user-provided YouTube cookies file: {path}")
            return path, False
        else:
            logger.warning(f"YOUTUBE_COOKIES_FILE set but file not found: {path}")

    # 2) base64-encoded cookies in env var
    tmp = _write_cookies_file()
    if tmp:
        return tmp, True

    return None, False


def _sanitize_filename(name: str) -> str:
    """Remove characters that are unsafe in file names."""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def download_video(
    youtube_url: str, job_id: str, audio_only: bool = False
) -> tuple[Path, str]:
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
    # By default download a smaller "processing" copy (e.g. 480p) to
    # speed up decoding/transcription. Consumers that only need audio can
    # request audio_only=True to download the audio stream instead.
    output_template = str(out_dir / "%(title)s.%(ext)s")

    if audio_only:
        fmt = "bestaudio"
    else:
        fmt = f"bestvideo[height<={settings.processing_max_height}]+bestaudio/best"

    cmd = [
        str(_YTDLP_BIN),
        "--format",
        fmt,
        "--merge-output-format",
        "mp4",
        "--output",
        output_template,
        "--no-playlist",
        "--no-warnings",
        "--print",
        "after_move:filepath",
        youtube_url,
    ]

    # Performance tuning: allow using an external downloader (aria2c) or
    # passing downloader args if configured in settings. This can speed up
    # downloads for fragmented streams (HLS/DASH) significantly.
    downloader = getattr(settings, "ytdlp_downloader", "").strip()
    downloader_args = getattr(settings, "ytdlp_downloader_args", "").strip()
    concurrent_fragments = int(getattr(settings, "ytdlp_concurrent_fragments", 0) or 0)
    if downloader:
        cmd.extend(["--downloader", downloader])
        if downloader_args:
            # pass the downloader args through --downloader-args
            cmd.extend(["--downloader-args", downloader_args])
    if concurrent_fragments > 0:
        cmd.extend(["--concurrent-fragments", str(concurrent_fragments)])

    # Inject YouTube cookies if available (required for datacenter IPs).
    # Support two methods:
    #  - YOUTUBE_COOKIES_FILE: path to a cookies.txt file (preferred)
    #  - YOUTUBE_COOKIES_B64: base64-encoded cookies file contents (legacy)
    cookies_file, cookies_is_temp = _get_cookies_file()
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
        logger.info(
            f"Using YouTube cookies for download (file={cookies_file}, temp={cookies_is_temp})"
        )

    # Decide whether to pass JS runtime / remote-components flags based on
    # configuration policy. This allows conservative behaviour in prod.
    js_runtimes = getattr(settings, "ytdlp_js_runtimes", "").strip()
    remote_components = getattr(settings, "ytdlp_remote_components", "").strip()
    enable_policy = getattr(settings, "ytdlp_enable_js", "when_cookies").strip().lower()

    def _with_js_flags(base_cmd):
        c = list(base_cmd)
        if js_runtimes:
            c.extend(["--js-runtimes", js_runtimes])
        if remote_components:
            c.extend(["--remote-components", remote_components])
        return c

    # If policy says always, enable flags now. If when_cookies, enable only if
    # a cookies file is present. If on_error, we will attempt first without
    # flags and only retry with flags if we detect a JS-challenge related error.
    should_pass_js_now = False
    if enable_policy == "always":
        should_pass_js_now = True
    elif enable_policy == "when_cookies":
        should_pass_js_now = bool(cookies_file)
    elif enable_policy == "on_error":
        should_pass_js_now = False
    else:
        # Unknown policy -> default to when_cookies
        should_pass_js_now = bool(cookies_file)

    base_cmd = list(cmd)
    if should_pass_js_now:
        cmd = _with_js_flags(base_cmd)

    logger.info(f"Running yt-dlp for job {job_id}: {youtube_url}")

    def _run_cmd(cmd_list):
        return subprocess.run(cmd_list, capture_output=True, text=True, check=True)

    result = None
    tried_impersonate = False
    try:
        try:
            # If policy is "on_error" and we didn't pre-enable JS flags, attempt
            # the base command first and only retry with JS flags on EJS-related
            # errors.
            if enable_policy == "on_error" and not should_pass_js_now:
                try:
                    result = _run_cmd(base_cmd)
                except subprocess.CalledProcessError as e:
                    stderr = (e.stderr or "").lower()
                    stdout = (e.stdout or "").lower()
                    logger.error(f"yt-dlp stderr: {e.stderr}")
                    logger.error(f"yt-dlp stdout: {e.stdout}")

                    # Detect EJS / JS-challenge related messages
                    ejs_msgs = [
                        "challenge solving failed",
                        "some formats may be missing",
                        "ensure you have a supported javascript",
                        "challenge",
                    ]
                    if any(m in stderr or m in stdout for m in ejs_msgs):
                        # Retry once with JS flags enabled
                        if js_runtimes or remote_components:
                            logger.info(
                                "Retrying yt-dlp with JS runtimes / remote-components to solve JS challenges"
                            )
                            try:
                                result = _run_cmd(_with_js_flags(base_cmd))
                            except subprocess.CalledProcessError as e2:
                                logger.error(f"yt-dlp retry stderr: {e2.stderr}")
                                logger.error(f"yt-dlp retry stdout: {e2.stdout}")
                                raise RuntimeError(
                                    f"yt-dlp failed (exit {e2.returncode}): {e2.stderr.strip() or e2.stdout.strip()}"
                                )
                        else:
                            raise RuntimeError(
                                f"yt-dlp failed (exit {e.returncode}): {e.stderr.strip() or e.stdout.strip()}"
                            )
                    else:
                        # Not an EJS-related error; reuse existing impersonation retry
                        bot_block_msgs = [
                            "sign in to confirm",
                            "confirm you",
                            "use --cookies",
                            "cookies",
                        ]
                        if any(m in stderr or m in stdout for m in bot_block_msgs):
                            help_msg = (
                                "yt-dlp a renvoyé une erreur indiquant que YouTube demande une vérification ("
                                "'Sign in to confirm you're not a bot'). Cela arrive souvent depuis des IP de datacenter ou "
                                "lorsque YouTube exige une session authentifiée."
                            )
                            suggestions = (
                                "Options pour résoudre le problème:\n"
                                '  1) Fournir des cookies YouTube exportés depuis votre navigateur via la variable d\'environnement "YOUTUBE_COOKIES_B64".\n'
                                "     - Exportez (ex: via l'extension 'EditThisCookie' ou 'cookies.txt') puis encodez en base64: \n"
                                "         cat cookies.txt | base64 | pbcopy  # macOS (copie dans le presse-papier)\n"
                                "       Puis définissez la variable d'environnement avant de démarrer le service:\n"
                                '         export YOUTUBE_COOKIES_B64="<contenu_base64>"\n'
                                "  2) (Temporaire) Réessayer avec une impersonation de navigateur. Le serveur va tenter ceci automatiquement une fois.\n"
                                "  3) Voir la doc yt-dlp pour passer des cookies: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp\n"
                            )
                            raise RuntimeError(
                                f"yt-dlp failed (exit {e.returncode}): {help_msg}\n\n{suggestions}"
                            )
                        if not cookies_file and not tried_impersonate:
                            tried_impersonate = True
                            logger.info(
                                "Retrying yt-dlp once with --impersonate chrome to bypass simple bot checks"
                            )
                            try:
                                retry_cmd = base_cmd + ["--impersonate", "chrome"]
                                result = _run_cmd(retry_cmd)
                            except subprocess.CalledProcessError as e2:
                                logger.error(f"yt-dlp retry stderr: {e2.stderr}")
                                logger.error(f"yt-dlp retry stdout: {e2.stdout}")
                                raise RuntimeError(
                                    f"yt-dlp failed (exit {e2.returncode}): {e2.stderr.strip() or e2.stdout.strip()}"
                                )
                        else:
                            raise RuntimeError(
                                f"yt-dlp failed (exit {e.returncode}): {e.stderr.strip() or e.stdout.strip()}"
                            )
            else:
                # Normal path: command already has flags if should_pass_js_now
                result = _run_cmd(cmd)
        except subprocess.CalledProcessError as e:
            # Capture output for analysis (when not handled above)
            stderr = (e.stderr or "").lower()
            stdout = (e.stdout or "").lower()
            logger.error(f"yt-dlp stderr: {e.stderr}")
            logger.error(f"yt-dlp stdout: {e.stdout}")

            bot_block_msgs = [
                "sign in to confirm",
                "confirm you",
                "use --cookies",
                "cookies",
            ]
            if any(m in stderr or m in stdout for m in bot_block_msgs):
                help_msg = (
                    "yt-dlp a renvoyé une erreur indiquant que YouTube demande une vérification ("
                    "'Sign in to confirm you're not a bot'). Cela arrive souvent depuis des IP de datacenter ou "
                    "lorsque YouTube exige une session authentifiée."
                )
                suggestions = (
                    "Options pour résoudre le problème:\n"
                    '  1) Fournir des cookies YouTube exportés depuis votre navigateur via la variable d\'environnement "YOUTUBE_COOKIES_B64".\n'
                    "     - Exportez (ex: via l'extension 'EditThisCookie' ou 'cookies.txt') puis encodez en base64: \n"
                    "         cat cookies.txt | base64 | pbcopy  # macOS (copie dans le presse-papier)\n"
                    "       Puis définissez la variable d'environnement avant de démarrer le service:\n"
                    '         export YOUTUBE_COOKIES_B64="<contenu_base64>"\n'
                    "  2) (Temporaire) Réessayer avec une impersonation de navigateur. Le serveur va tenter ceci automatiquement une fois.\n"
                    "  3) Voir la doc yt-dlp pour passer des cookies: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp\n"
                )
                raise RuntimeError(
                    f"yt-dlp failed (exit {e.returncode}): {help_msg}\n\n{suggestions}"
                )

            # Otherwise attempt a single retry with impersonation which can help
            # for some extractor blocks. Don't do this if user provided cookies
            # (they should be preferred).
            if not cookies_file and not tried_impersonate:
                tried_impersonate = True
                logger.info(
                    "Retrying yt-dlp once with --impersonate chrome to bypass simple bot checks"
                )
                try:
                    retry_cmd = cmd + ["--impersonate", "chrome"]
                    result = _run_cmd(retry_cmd)
                except subprocess.CalledProcessError as e2:
                    logger.error(f"yt-dlp retry stderr: {e2.stderr}")
                    logger.error(f"yt-dlp retry stdout: {e2.stdout}")
                    raise RuntimeError(
                        f"yt-dlp failed (exit {e2.returncode}): {e2.stderr.strip() or e2.stdout.strip()}"
                    )
            else:
                # Not a bot/blocking message we recognized and no retry available
                raise RuntimeError(
                    f"yt-dlp failed (exit {e.returncode}): {e.stderr.strip() or e.stdout.strip()}"
                )
    finally:
        # Clean up temp cookie file only if we created it
        try:
            if cookies_file and locals().get("cookies_is_temp"):
                os.unlink(cookies_file)
        except Exception:
            pass

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


def extract_audio(
    video_path: str | Path,
    out_wav: str | Path,
    start: float | None = None,
    duration: float | None = None,
) -> Path:
    """
    Extract a mono 16 kHz WAV suitable for ASR using ffmpeg.

    Parameters
    ----------
    video_path: path to source video file
    out_wav: output WAV path
    start: optional start time in seconds
    duration: optional duration in seconds

    Returns
    -------
    Path to the generated WAV file (raises on ffmpeg errors)
    """
    from subprocess import run, CalledProcessError

    video_path = str(video_path)
    out_wav = str(out_wav)
    cmd = ["ffmpeg", "-y"]
    if start is not None:
        # -ss before -i seeks faster (input seeking)
        cmd += ["-ss", str(start)]
    cmd += ["-i", video_path]
    if duration is not None:
        cmd += ["-t", str(duration)]
    # audio-only, mono, 16kHz WAV (widely supported for ASR)
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-f", "wav", out_wav]

    logger.info(f"Extracting audio: {' '.join(cmd)}")
    try:
        run(cmd, capture_output=True, text=True, check=True)
    except CalledProcessError as e:
        logger.error(f"ffmpeg stderr: {e.stderr}")
        logger.error(f"ffmpeg stdout: {e.stdout}")
        raise RuntimeError(f"ffmpeg failed: {e.stderr.strip() or e.stdout.strip()}")

    return Path(out_wav)
