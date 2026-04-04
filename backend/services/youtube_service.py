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
import time
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
    
    # If environment allows, attempt an automatic refresh using the
    # Playwright-based refresher script (scripts/refresh_youtube_cookies.py).
    # Enable by setting YOUTUBE_ENABLE_AUTO_REFRESH=true in the service env.
    def _attempt_auto_refresh() -> str | None:
        try:
            if os.environ.get("YOUTUBE_ENABLE_AUTO_REFRESH", "").lower() not in (
                "1",
                "true",
                "yes",
            ):
                return None

            # Locate the refresher script relative to this file (project_root/scripts/...)
            proj_root = Path(__file__).resolve().parents[2]
            script_path = proj_root / "scripts" / "refresh_youtube_cookies.py"
            if not script_path.exists():
                logger.warning(f"Auto-refresh requested but script not found: {script_path}")
                return None

            out_path = os.environ.get("YOUTUBE_AUTO_REFRESH_OUT", "/tmp/yt_cookies_refreshed.txt")
            cmd = [sys.executable, str(script_path), "--out", out_path]
            profile = os.environ.get("YOUTUBE_BROWSER_PROFILE_DIR")
            if profile:
                cmd.extend(["--profile", profile])
            # Optional canary URL to validate the cookies after refresh
            canary = os.environ.get("YOUTUBE_AUTO_REFRESH_CANARY")
            if canary:
                cmd.extend(["--canary", canary])

            # Optionally run headless by env var
            if os.environ.get("YOUTUBE_AUTO_REFRESH_HEADLESS", "1").lower() in ("1", "true", "yes"):
                cmd.append("--headless")

            logger.info(f"Attempting auto-refresh of YouTube cookies via: {script_path}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if proc.returncode != 0:
                logger.warning(
                    "Auto-refresh script failed",
                )
                logger.debug("auto-refresh stdout: %s", proc.stdout)
                logger.debug("auto-refresh stderr: %s", proc.stderr)
                return None

            # parse safe diagnostic line: WROTE <path> size=<bytes> sha256=<hex>
            import re as _re

            m = _re.search(r"WROTE\s+(\S+)\s+size=\s*(\d+)\s+sha256=([0-9a-fA-F]+)", proc.stdout)
            if not m:
                # Fallback: check stdout for a path
                logger.debug("auto-refresh produced no WROTE line; stdout: %s", proc.stdout)
                if os.path.exists(out_path):
                    return out_path
                return None

            refreshed_path = m.group(1)
            size = int(m.group(2))
            sha = m.group(3)
            # Log safe metadata
            logger.info(f"[YTC AUTOREFRESH] wrote {refreshed_path} size={size} sha256={sha}")
            if os.path.exists(refreshed_path):
                return refreshed_path
            # If script reported path but file missing, try configured out_path
            if os.path.exists(out_path):
                return out_path
            return None
        except Exception as exc:
            logger.exception("Auto-refresh attempt failed: %s", exc)
            return None

    refreshed = _attempt_auto_refresh()
    if refreshed:
        return refreshed, True
    return None, False


# Rate-limit cache for auto-refresh attempts: maps job_id -> last_refresh_timestamp
_AUTOREFRESH_RATELIMIT_CACHE: dict[str, float] = {}
_AUTOREFRESH_RATELIMIT_SECONDS = 3600  # 1 hour between auto-refreshes per job


def _auto_refresh_and_retry_download(
    base_cmd: list[str], job_id: str, youtube_url: str
) -> subprocess.CompletedProcess:
    """
    Attempt to refresh YouTube cookies via Playwright, then retry the download command.
    
    This function is called when yt-dlp fails with a "Sign in to confirm you're not a bot" error.
    It enforces a rate-limit (1 attempt per job per hour) to prevent excessive refresh calls.
    
    Returns the result of the retry yt-dlp run, or raises RuntimeError if refresh/retry fails.
    """
    # Rate-limit: check if we've attempted auto-refresh for this job recently
    last_refresh = _AUTOREFRESH_RATELIMIT_CACHE.get(job_id, 0)
    now = time.time()
    if now - last_refresh < _AUTOREFRESH_RATELIMIT_SECONDS:
        logger.warning(
            f"Auto-refresh rate-limited for job {job_id}. Last refresh: {int(now - last_refresh)}s ago. "
            f"Limit: {_AUTOREFRESH_RATELIMIT_SECONDS}s."
        )
        raise RuntimeError(
            f"yt-dlp failed and auto-refresh was rate-limited. "
            f"Cookies may have expired; try again in {_AUTOREFRESH_RATELIMIT_SECONDS}s."
        )
    
    logger.info(f"Auto-refresh triggered for job {job_id} due to bot-check failure.")
    
    # Invoke the Playwright refresher script
    try:
        proj_root = Path(__file__).resolve().parents[2]
        # Try multiple possible locations (project root, /app/scripts, /scripts)
        possible_paths = [
            proj_root / "scripts" / "refresh_youtube_cookies.py",  # development: project root
            Path("/app/scripts/refresh_youtube_cookies.py"),  # docker: /app layout
            Path("/scripts/refresh_youtube_cookies.py"),  # docker: root /scripts
        ]
        
        script_path = None
        for path in possible_paths:
            if path.exists():
                script_path = path
                logger.debug(f"Found refresher script at {script_path}")
                break
        
        if not script_path:
            logger.error(
                f"Auto-refresh script not found at any of: {possible_paths}. "
                "Ensure scripts/refresh_youtube_cookies.py is included in your Docker image. "
                "Add to Dockerfile: COPY scripts/refresh_youtube_cookies.py /app/scripts/ "
                "and install Playwright: RUN pip install -r scripts/requirements-playwright.txt && python3 -m playwright install"
            )
            raise RuntimeError(
                "Playwright refresher not found. Ensure scripts are deployed to the image. "
                "See logs for Dockerfile requirements."
            )

        out_path = os.environ.get("YOUTUBE_AUTO_REFRESH_OUT", "/tmp/yt_cookies_autorefresh.txt")
        
        # Ensure out_path is absolute (not relative), to avoid issues when subprocess runs from different cwd
        out_path = str(Path(out_path).resolve())
        
        # Ensure the parent directory exists
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        
        refresh_cmd = [sys.executable, str(script_path), "--out", out_path]
        
        profile = os.environ.get("YOUTUBE_BROWSER_PROFILE_DIR")
        if profile:
            refresh_cmd.extend(["--profile", profile])
        
        # Run headless by default in prod (unless explicitly disabled)
        if os.environ.get("YOUTUBE_AUTO_REFRESH_HEADLESS", "1").lower() in ("1", "true", "yes"):
            refresh_cmd.append("--headless")
        
        logger.info(f"Running Playwright refresher: {script_path}")
        refresh_proc = subprocess.run(refresh_cmd, capture_output=True, text=True, timeout=180)
        
        if refresh_proc.returncode != 0:
            logger.error(f"Playwright refresher failed with exit code {refresh_proc.returncode}")
            logger.error(f"refresher stdout: {refresh_proc.stdout}")
            logger.error(f"refresher stderr: {refresh_proc.stderr}")
            raise RuntimeError(f"Playwright refresher failed (exit {refresh_proc.returncode}): {refresh_proc.stderr or refresh_proc.stdout}")
        
        # Parse safe diagnostic: WROTE <path> size=<bytes> sha256=<hex>
        m = re.search(r"WROTE\s+(\S+)\s+size=\s*(\d+)\s+sha256=([0-9a-fA-F]+)", refresh_proc.stdout)
        if not m:
            logger.error(f"Refresher did not produce a WROTE line. stdout: {refresh_proc.stdout}")
            if not os.path.exists(out_path):
                raise RuntimeError("Playwright refresher failed to write cookies file")
            refreshed_path = out_path
        else:
            refreshed_path = m.group(1)
            size = int(m.group(2))
            sha = m.group(3)
            logger.info(f"[YTC AUTO-REFRESH] cookies refreshed: {refreshed_path} size={size} sha256={sha}")
        
        if not os.path.exists(refreshed_path):
            raise RuntimeError(f"Refreshed cookies file not found at {refreshed_path}")
        
        # Record this refresh in rate-limit cache
        _AUTOREFRESH_RATELIMIT_CACHE[job_id] = now
        
        # Retry the yt-dlp command with the refreshed cookies
        logger.info(f"Retrying yt-dlp with refreshed cookies for job {job_id}: {youtube_url}")
        retry_cmd = list(base_cmd)
        
        # Replace or add --cookies flag
        try:
            cookies_idx = retry_cmd.index("--cookies")
            retry_cmd[cookies_idx + 1] = refreshed_path
        except (ValueError, IndexError):
            # --cookies not in command; add it
            retry_cmd.extend(["--cookies", refreshed_path])
        
        result = subprocess.run(retry_cmd, capture_output=True, text=True, check=True)
        logger.info(f"yt-dlp retry succeeded for job {job_id}")
        return result
    
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp retry failed after refresh: {e.stderr or e.stdout}")
        raise RuntimeError(
            f"yt-dlp failed even after refreshing cookies (exit {e.returncode}). "
            f"Error: {e.stderr.strip() or e.stdout.strip()}"
        )
    except Exception as e:
        logger.exception(f"Auto-refresh and retry failed: {e}")
        raise RuntimeError(f"Auto-refresh and retry failed: {e}")


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
        # Use YouTube-specific resolution for high quality shorts
        max_height = getattr(settings, "youtube_processing_max_height", settings.processing_max_height)
        fmt = f"bestvideo[height<={max_height}]+bestaudio/best"

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
                        # Not an EJS-related error; check for bot-check / auth errors
                        bot_block_msgs = [
                            "sign in to confirm",
                            "confirm you",
                            "use --cookies",
                            "cookies",
                        ]
                        if any(m in stderr or m in stdout for m in bot_block_msgs):
                            # Bot-check detected. Try to auto-refresh cookies and retry
                            # (if Playwright refresher is available and rate-limit allows).
                            try:
                                logger.info(f"Bot-check detected; attempting auto-refresh and retry for job {job_id}")
                                result = _auto_refresh_and_retry_download(base_cmd, job_id, youtube_url)
                            except RuntimeError as auto_refresh_err:
                                # Auto-refresh failed or was rate-limited. Provide helpful error message.
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
                                    "  2) Activer le rafraîchissement automatique des cookies via Playwright (YOUTUBE_ENABLE_AUTO_REFRESH=true).\n"
                                    "  3) Voir la doc yt-dlp pour passer des cookies: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp\n"
                                )
                                raise RuntimeError(
                                    f"yt-dlp failed and auto-refresh failed: {str(auto_refresh_err)}\n\n{help_msg}\n\n{suggestions}"
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
                # Bot-check detected. Try to auto-refresh cookies and retry
                # (if Playwright refresher is available and rate-limit allows).
                try:
                    logger.info(f"Bot-check detected; attempting auto-refresh and retry for job {job_id}")
                    result = _auto_refresh_and_retry_download(cmd, job_id, youtube_url)
                except RuntimeError as auto_refresh_err:
                    # Auto-refresh failed or was rate-limited. Provide helpful error message.
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
                        "  2) Activer le rafraîchissement automatique des cookies via Playwright (YOUTUBE_ENABLE_AUTO_REFRESH=true).\n"
                        "  3) Voir la doc yt-dlp pour passer des cookies: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp\n"
                    )
                    raise RuntimeError(
                        f"yt-dlp failed and auto-refresh failed: {str(auto_refresh_err)}\n\n{help_msg}\n\n{suggestions}"
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
