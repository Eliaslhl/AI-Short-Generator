"""
routes.py – All API endpoints for the AI Shorts Generator.

Endpoints
---------
POST /api/generate        – start a generation job (requires auth + quota)
GET  /api/status/{job_id} – poll job progress
GET  /api/clips/{job_id}  – list finished clips for a job
GET  /api/history         – user's past jobs
"""

import uuid
import asyncio
import logging
from typing import Dict, Any
import os
import hashlib

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User, Job
from backend.auth.dependencies import get_current_user
from backend.services.youtube_service import download_video as download_youtube, _get_cookies_file
from backend.services.twitch_service import download_video as download_twitch
from backend.services.twitch_api_client import TwitchAPIClient
from backend.config import settings
from backend.services.clip_selector import select_top_segments
from backend.services.hook_service import generate_hook
from backend.services.emoji_caption_service import build_captions
from backend.services.title_service import generate_title
from backend.services.hashtag_service import generate_hashtags
from backend.video.video_editor import render_clip

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory job store (progress tracking) ─────────────────────────────────
jobs: Dict[str, Dict[str, Any]] = {}


def _detect_platform_from_url(url: str) -> str:
    return "twitch" if "twitch.tv" in (url or "").lower() else "youtube"


def _get_platform_plan(user: User, platform: str):
    if platform == "twitch":
        return user.plan_twitch or user.plan
    return user.plan_youtube or user.plan


def _get_platform_limit(user: User, platform: str) -> int:
    return user.twitch_limit if platform == "twitch" else user.youtube_limit


def _get_platform_usage(user: User, platform: str) -> int:
    return (
        int(user.twitch_generations_month or 0)
        if platform == "twitch"
        else int(user.youtube_generations_month or 0)
    )


def _increment_platform_usage(user: User, platform: str) -> None:
    if platform == "twitch":
        user.twitch_generations_month = int(user.twitch_generations_month or 0) + 1
    else:
        user.youtube_generations_month = int(user.youtube_generations_month or 0) + 1
        # Keep legacy field aligned with YouTube for backward compatibility
        user.generations_this_month = int(user.youtube_generations_month or 0)


def _decrement_platform_usage(user: User, platform: str) -> bool:
    if platform == "twitch":
        cur = int(user.twitch_generations_month or 0)
        if cur <= 0:
            return False
        user.twitch_generations_month = cur - 1
        return True

    cur = int(user.youtube_generations_month or 0)
    if cur <= 0:
        return False
    user.youtube_generations_month = cur - 1
    user.generations_this_month = int(user.youtube_generations_month or 0)
    return True


async def _reset_platform_counter_if_new_month(user: User, db: AsyncSession, platform: str) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    last_reset = user.twitch_plan_reset_date if platform == "twitch" else user.youtube_plan_reset_date
    if last_reset is None:
        if platform == "twitch":
            user.twitch_plan_reset_date = now
        else:
            user.youtube_plan_reset_date = now
            user.plan_reset_date = now
        await db.commit()
        await db.refresh(user)
        return

    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    if (now.year, now.month) > (last_reset.year, last_reset.month):
        if platform == "twitch":
            user.twitch_generations_month = 0
            user.twitch_plan_reset_date = now
        else:
            user.youtube_generations_month = 0
            user.youtube_plan_reset_date = now
            user.generations_this_month = 0
            user.plan_reset_date = now
        await db.commit()
        await db.refresh(user)


def _normalize_clip_for_response(clip: dict, job_id: str) -> dict:
    """Return a safe, frontend-friendly clip dict.

    This function adds compatibility fields the frontend may expect:
    - url: primary URL to access the clip (falls back to path)
    - thumbnail: thumbnail path/url
    - duration: duration in seconds
    - title: human-friendly title

    We do not remove original fields; we only ensure commonly expected
    names are present so the UI can display clips without frontend changes.
    """
    out = dict(clip) if isinstance(clip, dict) else {"path": str(clip)}

    # url: prefer existing 'url', then 'path'
    if "url" not in out or not out.get("url"):
        out["url"] = out.get("path") or out.get("file") or None

    # thumbnail: prefer existing 'thumbnail' or 'thumb'
    if "thumbnail" not in out or not out.get("thumbnail"):
        thumb = out.get("thumbnail") or out.get("thumb")
        if not thumb and out.get("url"):
            # try to derive thumbnail filename by replacing extension
            try:
                from pathlib import Path

                p = Path(out["url"])
                derived = str(p.with_suffix(".jpg"))
                out["thumbnail"] = derived
            except Exception:
                out["thumbnail"] = None
        else:
            out["thumbnail"] = thumb

    # duration: normalize common keys
    if "duration" not in out or not out.get("duration"):
        out["duration"] = out.get("len") or out.get("length") or out.get("duration_seconds") or None

    # title: fallback to file basename
    if "title" not in out or not out.get("title"):
        try:
            from pathlib import Path

            if out.get("url"):
                out["title"] = Path(out["url"]).stem
            elif out.get("path"):
                out["title"] = Path(out["path"]).stem
            else:
                out["title"] = None
        except Exception:
            out["title"] = None

    # include job_id for convenience
    out.setdefault("job_id", job_id)
    return out


# ── Request / Response models ────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    youtube_url: str
    max_clips: int = 3  # FREE default; enforced server-side per plan
    language: str = ""  # "" = auto-detect; ISO-639-1 code for PRO (e.g. "fr")
    subtitle_style: str = "default"  # PRO: default | bold | outlined | neon | minimal
    transcription_mode: str = ""  # optional: "FAST" (default) or "QUALITY" (Pro+ only)


class GenerateResponse(BaseModel):
    job_id: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    step: str
    clips: list


class PreviewRequest(BaseModel):
    url: str


class PreviewResponse(BaseModel):
    url: str
    title: str | None = None
    duration: float | None = None
    thumbnail: str | None = None


class TwitchVodsRequest(BaseModel):
    channel_login: str
    limit: int = 20


class TwitchVodItem(BaseModel):
    id: str
    title: str | None = None
    created_at: str | None = None
    duration: int | None = None
    view_count: int | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    channel_name: str | None = None


class TwitchVodsResponse(BaseModel):
    channel_login: str
    vods: list[TwitchVodItem]


# ── Background pipeline ──────────────────────────────────────────────────────
async def run_pipeline(
    job_id: str,
    youtube_url: str,
    user_id: str,
    max_clips: int = 3,
    language: str = "",
    subtitle_style: str = "default",
    is_proplus: bool = False,
    transcription_mode: str | None = None,
):
    """Full async pipeline: download → transcribe → score → render."""
    platform = _detect_platform_from_url(youtube_url)

    async def update(progress: int, step: str):
        """Update in-memory status and persist progress to DB.

        Persisting progress ensures that if a user navigates away or the
        process is restarted, status can be restored from the database.
        """
        jobs[job_id]["progress"] = progress
        jobs[job_id]["step"] = step
        logger.info(f"[{job_id}] {progress}% – {step}")

        # Persist a light-weight progress update to the DB so status survives
        # process restarts or client navigation.
        try:
            from backend.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Job).where(Job.id == job_id))
                job_record = result.scalar_one_or_none()
                if job_record:
                    job_record.progress = progress
                    job_record.status = jobs[job_id].get("status", job_record.status)
                    job_record.clips_json = (
                        job_record.clips_json or job_record.clips_json
                    )
                    await db.commit()
        except Exception:
            # Don't let persistence failures interrupt the pipeline; just log.
            logger.debug(f"Failed to persist job progress for {job_id}", exc_info=True)

    try:
        jobs[job_id]["status"] = "processing"

        # Detect source (YouTube or Twitch)
        is_twitch = "twitch.tv" in youtube_url.lower()
        source_name = "Twitch" if is_twitch else "YouTube"
        
        await update(5, f"Downloading video from {source_name}…")
        
        # Download from appropriate service
        if is_twitch:
            video_path, video_title = await asyncio.to_thread(
                download_twitch, youtube_url, job_id
            )
        else:
            video_path, video_title = await asyncio.to_thread(
                download_youtube, youtube_url, job_id
            )
        jobs[job_id]["video_title"] = video_title

        await update(20, "Transcribing audio with Faster-Whisper…")
        # Determine transcription mode: default FAST. Only allow QUALITY for pro/proplus users.
        mode = (transcription_mode or "").upper() if transcription_mode else ""
        if mode == "QUALITY":
            # only allow QUALITY for pro or proplus; is_proplus covers proplus, check DB for pro below
            # We'll conservatively allow QUALITY only if is_proplus is True; otherwise fallback to FAST.
            if not is_proplus:
                logger.info(
                    f"Job {job_id}: QUALITY mode requested but not allowed for this plan; falling back to FAST."
                )
                mode = "FAST"
        if mode not in ("QUALITY", "FAST"):
            mode = "FAST"

        from backend.services.transcription_service import transcribe_for_job

        segments = await asyncio.to_thread(
            transcribe_for_job, str(video_path), mode, language or None
        )

        # Get video duration for precise padding/clamping
        import subprocess
        import json as _json

        def _get_duration(path: str) -> float:
            r = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    str(path),
                ],
                capture_output=True,
                text=True,
            )
            return float(_json.loads(r.stdout)["format"]["duration"])

        video_duration = await asyncio.to_thread(_get_duration, str(video_path))

        await update(40, "Analysing and scoring segments…")
        top_segments = await asyncio.to_thread(
            select_top_segments, segments, max_clips, video_duration
        )
        # Ensure clips are rendered in chronological order (video timeline order)
        # so the generated shorts follow the source video sequence instead of
        # the ranking order returned by select_top_segments.
        top_segments.sort(key=lambda s: s.get("start", 0.0))

        await update(55, "Generating viral hooks with local LLM…")
        for seg in top_segments:
            seg["hook"] = await asyncio.to_thread(generate_hook, seg["text"])

        # Pro+ only: auto title + auto hashtags
        if is_proplus:
            await update(60, "Generating titles & hashtags (Pro+)…")
            for seg in top_segments:
                seg["ai_title"] = await asyncio.to_thread(generate_title, seg["text"])
                seg["hashtags"] = await asyncio.to_thread(
                    generate_hashtags, seg["text"]
                )

        await update(65, "Building emoji captions…")
        for seg in top_segments:
            seg["captions"] = await asyncio.to_thread(
                build_captions,
                seg["text"],
                seg.get("words"),  # word-level timestamps for accurate sync
            )

        clips = []
        total = len(top_segments)
        for idx, seg in enumerate(top_segments):
            pct = 75 + int((idx / total) * 22)
            await update(pct, f"Rendering clip {idx + 1}/{total}…")
            try:
                clip_info = await asyncio.to_thread(
                    render_clip,
                    video_path=str(video_path),
                    segment=seg,
                    job_id=job_id,
                    clip_index=idx,
                    subtitle_style=subtitle_style,
                )
            except Exception as e:
                logger.exception(f"Failed to render clip {idx + 1}/{total} for job {job_id}: {e}")
                # Persist error state and refund credit
                jobs[job_id]["status"] = "error"
                jobs[job_id]["step"] = f"Error rendering clip: {e}"
                from backend.database import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job_record = result.scalar_one_or_none()
                    if job_record:
                        job_record.status = "error"
                        job_record.error = str(e)
                        # refund credit
                        user_result = await db.execute(select(User).where(User.id == user_id))
                        user_record = user_result.scalar_one_or_none()
                        if user_record:
                            refunded = _decrement_platform_usage(user_record, platform)
                            if refunded:
                                logger.info(
                                    f"Refunded {platform} generation credit for user {user_id} (job {job_id} failed during render)"
                                )
                        await db.commit()
                raise

            clips.append(clip_info)

            # Persist the partially rendered clips immediately so the UI can show
            # them while the rest of the pipeline continues.
            jobs[job_id]["clips"] = clips.copy()
            # Log minimal clip info for debugging (keys and common fields)
            try:
                import json as _json
                keys = list(clip_info.keys()) if isinstance(clip_info, dict) else []
                info_preview = {
                    "keys": keys,
                    "path": clip_info.get("path") if isinstance(clip_info, dict) else None,
                    "thumbnail": clip_info.get("thumbnail") if isinstance(clip_info, dict) else None,
                }
                logger.info(f"[{job_id}] rendered clip preview: {_json.dumps(info_preview)}")
            except Exception:
                logger.debug(f"[{job_id}] unable to stringify clip_info for logging", exc_info=True)
            try:
                from backend.database import AsyncSessionLocal
                import json as _json

                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job_record = result.scalar_one_or_none()
                    if job_record:
                        job_record.clips_json = _json.dumps(clips)
                        job_record.progress = jobs[job_id].get("progress", job_record.progress)
                        await db.commit()
            except Exception:
                logger.debug(f"Failed to persist partial clips for job {job_id}", exc_info=True)

        await update(100, "All clips are ready!")
        jobs[job_id]["status"] = "done"
        jobs[job_id]["clips"] = clips

        # Persist job result to DB
        import json
        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job_record = result.scalar_one_or_none()
            if job_record:
                job_record.status = "done"
                job_record.progress = 100
                job_record.video_title = video_title
                job_record.clips_json = json.dumps(clips)
                await db.commit()

    except Exception as exc:
        logger.exception(f"Pipeline error for job {job_id}: {exc}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["step"] = f"Error: {exc}"

        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job_record = result.scalar_one_or_none()
            if job_record:
                job_record.status = "error"
                job_record.error = str(exc)
                # ── Refund the generation credit on failure ──────────────────
                user_result = await db.execute(select(User).where(User.id == user_id))
                user_record = user_result.scalar_one_or_none()
                if user_record:
                    refunded = _decrement_platform_usage(user_record, platform)
                    if refunded:
                        logger.info(
                            f"Refunded {platform} generation credit for user {user_id} (job {job_id} failed)"
                        )
                await db.commit()


        # Debug endpoint: return size and sha256 of reconstructed YouTube cookies file
        # Only available when YOUTUBE_COOKIES_DEBUG is enabled to avoid leaking secrets.
        @router.get("/debug/youtube-cookies")
        async def debug_youtube_cookies():
            if os.environ.get("YOUTUBE_COOKIES_DEBUG", "").lower() not in ("1", "true", "yes"):
                # Hide endpoint when not enabled
                raise HTTPException(status_code=404, detail="Not found")

            cookies_file, cookies_is_temp = _get_cookies_file()
            if not cookies_file:
                return JSONResponse({"found": False})

            try:
                size = os.path.getsize(cookies_file)
                with open(cookies_file, "rb") as fh:
                    sha = hashlib.sha256(fh.read()).hexdigest()
            finally:
                # cleanup only if we created a temp file
                try:
                    if cookies_file and cookies_is_temp:
                        os.unlink(cookies_file)
                except Exception:
                    pass

            return JSONResponse({"found": True, "size": size, "sha256": sha})


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a generation job. Requires auth + quota check."""
    job_id = str(uuid.uuid4())[:8]

    platform = _detect_platform_from_url(request.youtube_url)
    await _reset_platform_counter_if_new_month(user, db, platform)

    usage = _get_platform_usage(user, platform)
    limit = _get_platform_limit(user, platform)
    if usage >= limit:
        plan_obj = _get_platform_plan(user, platform)
        plan_name = plan_obj.value if hasattr(plan_obj, "value") else str(plan_obj)
        source_label = "Twitch" if platform == "twitch" else "YouTube"
        message = (
            f"You've used all {limit} of your {plan_name} plan generations this month "
            f"for {source_label}."
        )
        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "message": message,
                "platform": platform,
                "limit": limit,
                "used": usage,
                "upgrade_url": "/pricing",
            },
        )

    # Enforce max_clips per plan server-side
    plan_obj = _get_platform_plan(user, platform)
    plan = plan_obj.value if hasattr(plan_obj, "value") else str(plan_obj)
    if plan == "proplus":
        allowed_clips = max(1, min(request.max_clips, 20))
    elif plan == "pro":
        allowed_clips = max(1, min(request.max_clips, 10))
    elif plan == "standard":
        allowed_clips = max(1, min(request.max_clips, 5))
    else:  # free
        allowed_clips = max(1, min(request.max_clips, 3))

    # Create DB record
    job_record = Job(
        id=job_id,
        user_id=user.id,
        youtube_url=request.youtube_url,
        status="pending",
        progress=0,
    )
    db.add(job_record)

    # Increment generation counter
    _increment_platform_usage(user, platform)
    await db.commit()

    # Init in-memory progress tracker
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "step": "Queued",
        "clips": [],
        "user_id": user.id,
    }

    # Language: standard and above can specify; free always uses auto-detect
    language = request.language if plan != "free" else ""

    # Subtitle style: standard and above can pick; free always uses default
    subtitle_style = request.subtitle_style if plan != "free" else "default"

    # Schedule the pipeline as an independent asyncio Task so it continues
    # running even if the client's request/connection is closed or the user
    # navigates away. Using BackgroundTasks ties execution to the request
    # lifecycle in some environments, so we prefer create_task here.
    asyncio.create_task(
        run_pipeline(
            job_id,
            request.youtube_url,
            user.id,
            allowed_clips,
            language,
            subtitle_style,
            plan == "proplus",
        )
    )
    return GenerateResponse(job_id=job_id, message="Job started.")


@router.post("/preview", response_model=PreviewResponse)
async def preview(
    request: PreviewRequest,
    user: User = Depends(get_current_user),
):
    """Return lightweight metadata for a YouTube or Twitch URL using yt-dlp.

    This endpoint runs yt-dlp in "print-json" mode without downloading the full
    video so the frontend can show a preview (title, duration, thumbnail).
    """
    url = request.url.strip()
    # Basic validation
    if not url:
        raise HTTPException(status_code=400, detail="Empty URL")

    # Use yt-dlp installed in the same virtualenv
    import sys
    from pathlib import Path
    import subprocess
    import json as _json

    venv_bin = Path(sys.executable).parent
    ytdlp = venv_bin / "yt-dlp"

    if not ytdlp.exists():
        raise HTTPException(status_code=500, detail="yt-dlp not available on server")

    cmd = [str(ytdlp), "-j", "--no-warnings", "--skip-download", url]
    try:
        proc = await asyncio.to_thread(
            lambda: subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        )
        info = _json.loads(proc.stdout)
        title = info.get("title") or info.get("fulltitle")
        duration = float(info.get("duration")) if info.get("duration") else None
        # Try common thumbnail keys
        thumbnail = info.get("thumbnail") or info.get("thumbnails") and (info.get("thumbnails")[-1].get("url") if isinstance(info.get("thumbnails"), list) and info.get("thumbnails") else None)
        return PreviewResponse(url=url, title=title, duration=duration, thumbnail=thumbnail)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"yt-dlp failed: {e.stderr or e.stdout or str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twitch/vods", response_model=TwitchVodsResponse)
async def get_twitch_vods(
    request: TwitchVodsRequest,
    user: User = Depends(get_current_user),
):
    """Fetch VODs for a Twitch channel using Client Credentials flow.

    Requires TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET environment variables.
    """
    import os

    client_id = os.environ.get("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Twitch API credentials not configured on server (TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET)",
        )

    channel_login = request.channel_login.strip().lower()
    if not channel_login:
        raise HTTPException(status_code=400, detail="channel_login cannot be empty")

    try:
        async with TwitchAPIClient(client_id, client_secret) as client:
            vods = await client.get_vods(channel_login, limit=request.limit)
            return TwitchVodsResponse(
                channel_login=channel_login,
                vods=[TwitchVodItem(**vod) for vod in vods],
            )
    except RuntimeError as e:
        logger.warning(f"Twitch API error for channel {channel_login}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error fetching Twitch VODs for {channel_login}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fast path: job still in memory
    if job_id in jobs:
        job = jobs[job_id]
        if job.get("user_id") and job["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        # Normalize clips for frontend compatibility
        raw_clips = job.get("clips", []) or []
        normalized = [_normalize_clip_for_response(c, job_id) for c in raw_clips]
        return StatusResponse(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            step=job["step"],
            clips=normalized,
        )

    # Fallback: job lost from memory (container restart) — reload from DB
    import json

    result = await db.execute(select(Job).where(Job.id == job_id))
    job_record = result.scalar_one_or_none()
    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    clips = json.loads(job_record.clips_json) if job_record.clips_json else []
    step = (
        "done"
        if job_record.status == "done"
        else (job_record.error or job_record.status)
    )
    progress = 100 if job_record.status == "done" else 0

    # Restore into memory so subsequent polls are fast
    jobs[job_id] = {
        "status": job_record.status,
        "progress": progress,
        "step": step,
        "clips": clips,
        "user_id": user.id,
    }
    normalized = [_normalize_clip_for_response(c, job_id) for c in clips]
    return StatusResponse(
        job_id=job_id,
        status=job_record.status,
        progress=progress,
        step=step,
        clips=normalized,
    )


@router.get("/clips/{job_id}")
async def get_clips(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import json

    if job_id in jobs:
        return JSONResponse(
            {
                "clips": jobs[job_id].get("clips", []),
                "video_title": jobs[job_id].get("video_title"),
                "status": jobs[job_id].get("status"),
            }
        )
    # Fallback to DB
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )
    job_record = result.scalar_one_or_none()
    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")
    clips = json.loads(job_record.clips_json) if job_record.clips_json else []
    return JSONResponse(
        {
            "clips": clips,
            "video_title": job_record.video_title,
            "status": job_record.status,
        }
    )


@router.get("/history")
async def get_history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Return all past jobs for the current user."""
    import json
    from datetime import datetime, timezone, timedelta

    # Only show jobs created within the last 1 hour (ephemeral storage policy)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(Job)
        .where(Job.user_id == user.id, Job.created_at >= cutoff)
        .order_by(Job.created_at.desc())
    )
    job_records = result.scalars().all()
    history = []
    for j in job_records:
        clips = json.loads(j.clips_json) if j.clips_json else []
        clips_count = len(clips)
        # Aggregate hashtags from clips (preserve order, unique) and limit to 5
        seen = set()
        hashtags = []
        for c in clips:
            hs = c.get("hashtags") if isinstance(c, dict) else None
            if not hs:
                continue
            for tag in hs:
                if tag and tag not in seen:
                    seen.add(tag)
                    hashtags.append(tag)
                    if len(hashtags) >= 5:
                        break
            if len(hashtags) >= 5:
                break
        expires_at = (
            (j.created_at + timedelta(hours=1)).astimezone(timezone.utc).isoformat()
        )
        history.append(
            {
                "id": j.id,
                "youtube_url": j.youtube_url,
                "video_title": j.video_title,
                "status": j.status,
                "clips_count": clips_count,
                "created_at": j.created_at.isoformat(),
                "expires_at": expires_at,
                "clips_url": f"/clips/{j.id}",
                "hashtags": hashtags,
            }
        )

    return JSONResponse({"history": history})


# ── Debug / Diagnostic endpoints ────────────────────────────────────────────
@router.post("/debug/refresh-cookies")
async def debug_refresh_cookies():
    """
    [DEBUG ONLY] Manually trigger a YouTube cookies refresh for testing.

    This endpoint attempts to run the Playwright refresher script and returns
    safe diagnostic information (size + sha256, not the cookie contents).

    Useful for testing the auto-refresh mechanism without waiting for real
    cookie expiration.

    Returns
    -------
    {
        "status": "success" | "failed",
        "diagnostic": "WROTE ... size=... sha256=...",
        "profile_dir": "<path>",
        "output_path": "<path>",
        "message": "<error detail if failed>"
    }
    """
    try:
        import subprocess
        import sys
        import os
        from pathlib import Path
        import re as regex_module

        # Locate the refresher script
        proj_root = Path(__file__).resolve().parents[2]
        script_path = proj_root / "scripts" / "refresh_youtube_cookies.py"

        if not script_path.exists():
            return JSONResponse(
                {
                    "status": "failed",
                    "message": f"Refresher script not found: {script_path}",
                },
                status_code=500,
            )

        # Build the refresh command
        out_path = os.environ.get("YOUTUBE_AUTO_REFRESH_OUT", "/tmp/yt_cookies_debug.txt")
        cmd = [sys.executable, str(script_path), "--out", out_path]

        profile = os.environ.get("YOUTUBE_BROWSER_PROFILE_DIR")
        if profile:
            cmd.extend(["--profile", profile])

        if os.environ.get("YOUTUBE_AUTO_REFRESH_HEADLESS", "1").lower() in ("1", "true", "yes"):
            cmd.append("--headless")

        logger.info(f"[DEBUG] Running refresher: {script_path}")

        # Run the refresher with a timeout
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if proc.returncode != 0:
            logger.error(f"[DEBUG] Refresher failed: {proc.stderr}")
            return JSONResponse(
                {
                    "status": "failed",
                    "profile_dir": profile,
                    "output_path": out_path,
                    "message": f"Refresher exited with code {proc.returncode}",
                    "stderr": proc.stderr[:500],  # truncate long errors
                },
                status_code=500,
            )

        # Parse the safe diagnostic line
        diagnostic_line = ""
        m = regex_module.search(r"WROTE\s+(\S+)\s+size=\s*(\d+)\s+sha256=([0-9a-fA-F]+)", proc.stdout)
        if m:
            refreshed_path = m.group(1)
            size = int(m.group(2))
            sha = m.group(3)
            diagnostic_line = f"WROTE {refreshed_path} size={size} sha256={sha}"
            logger.info(f"[DEBUG] {diagnostic_line}")

        return JSONResponse(
            {
                "status": "success",
                "diagnostic": diagnostic_line,
                "profile_dir": profile,
                "output_path": out_path,
                "message": "Cookies refreshed successfully (if profile was configured with authenticated session)",
            }
        )

    except subprocess.TimeoutExpired:
        return JSONResponse(
            {
                "status": "failed",
                "message": "Refresher timed out (180s). Check if Playwright is installed and profile is valid.",
            },
            status_code=500,
        )
    except Exception as e:
        logger.exception(f"[DEBUG] Refresh-cookies endpoint error: {e}")
        return JSONResponse(
            {
                "status": "failed",
                "message": f"Unexpected error: {str(e)}",
            },
            status_code=500,
        )


@router.get("/debug/job/{job_id}")
async def debug_job(job_id: str, user: User = Depends(get_current_user)):
    """
    Debug endpoint: return in-memory job state and DB record for a given job_id.
    Use this to inspect why a job is still processing or to retrieve error details.
    """
    # First check in-memory state
    in_memory = jobs.get(job_id)

    # Then fetch DB row
    try:
        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job_record = result.scalar_one_or_none()
            db_row = None
            if job_record:
                db_row = {
                    "id": job_record.id,
                    "status": job_record.status,
                    "progress": job_record.progress,
                    "video_title": job_record.video_title,
                    "error": job_record.error,
                    "clips_json": job_record.clips_json,
                    "created_at": job_record.created_at.isoformat() if job_record.created_at else None,
                }
    except Exception:
        db_row = None

    return JSONResponse({"in_memory": in_memory, "db": db_row})
