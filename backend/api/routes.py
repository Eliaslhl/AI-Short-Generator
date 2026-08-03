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

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, StrictBool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User, Job
from backend.auth.dependencies import get_current_user
from backend.services.youtube_service import download_video as download_youtube
from backend.services.twitch_service import download_video as download_twitch
from backend.services.twitch_api_client import TwitchAPIClient
from backend.config import settings
from backend.services.clip_selector import select_top_segments
from backend.services.hook_service import generate_hook
from backend.services.emoji_caption_service import build_captions
from backend.services.title_service import generate_title, normalize_supported_language
from backend.services.hashtag_service import generate_hashtags
from backend.services.job_access_service import job_access_service
from backend.services.transcription_service import TranscriptionMode
from backend.video.video_editor import render_clip
from backend.services.private_media_service import (
    InvalidRange,
    MediaNotFound,
    clip_at,
    close_clip,
    filename,
    media_type,
    open_clip,
    parse_range,
    public_clip_payloads,
    stream,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class _PrivateMediaStreamingResponse(StreamingResponse):
    """Close the owned descriptor even when ASGI aborts a stream early."""

    def __init__(self, opened_clip, start: int, end: int, **kwargs):
        self._opened_clip = opened_clip
        super().__init__(stream(opened_clip, start, end), **kwargs)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            close_clip(self._opened_clip)

# ── In-memory job store (progress tracking) ─────────────────────────────────
jobs: Dict[str, Dict[str, Any]] = {}


def _detect_platform_from_url(url: str) -> str:
    return "twitch" if "twitch.tv" in (url or "").lower() else "youtube"


def _detected_transcript_language(segments: list[dict[str, Any]]) -> str | None:
    """Read optional language metadata without attempting text-based detection."""
    for segment in segments:
        language = segment.get("detected_language") or segment.get("language")
        if isinstance(language, str) and language.strip():
            return language
    return None


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


# ── Request / Response models ────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    youtube_url: str
    max_clips: int = 3  # FREE default; enforced server-side per plan
    language: str = ""  # "" = auto-detect; ISO-639-1 code for PRO (e.g. "fr")
    subtitle_style: str = "default"  # PRO: default | bold | outlined | neon | minimal
    transcription_mode: TranscriptionMode | None = None
    include_subtitles: StrictBool | None = None


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
    transcription_mode: TranscriptionMode | None = None,
    include_subtitles: bool | None = None,
):
    """Full async pipeline: download → transcribe → score → render."""
    platform = _detect_platform_from_url(youtube_url)
    subtitles_enabled = (
        settings.include_subtitles_by_default
        if include_subtitles is None
        else include_subtitles
    )
    logger.info("[%s] subtitles_enabled=%s", job_id, subtitles_enabled)

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
        mode = (
            TranscriptionMode.FAST
            if transcription_mode is None
            else transcription_mode
        )
        if not isinstance(mode, TranscriptionMode):
            raise ValueError("Unsupported transcription mode")
        if mode is TranscriptionMode.QUALITY and not is_proplus:
            raise ValueError("QUALITY transcription requires a Pro+ plan")

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

        from backend.services.transcription_service import transcribe_for_job

        requested_language = (
            language.strip() if language and language.strip().lower() != "auto" else None
        )
        segments = await asyncio.to_thread(
            transcribe_for_job,
            str(video_path),
            transcription_mode=mode,
            language=requested_language,
        )
        title_language = (
            normalize_supported_language(requested_language)
            or normalize_supported_language(_detected_transcript_language(segments))
            or "en"
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
                seg["ai_title"] = await asyncio.to_thread(
                    generate_title,
                    seg["text"],
                    language=title_language,
                )
                seg["hashtags"] = await asyncio.to_thread(
                    generate_hashtags, seg["text"]
                )

        if subtitles_enabled:
            await update(65, "Building emoji captions…")
            for seg in top_segments:
                seg["captions"] = await asyncio.to_thread(
                    build_captions,
                    seg["text"],
                    seg.get("words"),  # word-level timestamps for accurate sync
                )
        else:
            await update(65, "Preparing clips without subtitles…")
            for seg in top_segments:
                seg["captions"] = None

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
            except Exception as exc:
                logger.error(
                    "Failed to render clip %s/%s for job %s: exception_type=%s",
                    idx + 1,
                    total,
                    job_id,
                    type(exc).__name__,
                )
                # Persist error state and refund credit
                jobs[job_id]["status"] = "error"
                jobs[job_id]["step"] = "A clip could not be rendered"
                from backend.database import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job_record = result.scalar_one_or_none()
                    if job_record:
                        job_record.status = "error"
                        job_record.error = "A clip could not be rendered"
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
            logger.info("Rendered clip %s/%s for job %s", idx + 1, total, job_id)
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
        logger.error("Pipeline error for job %s: exception_type=%s", job_id, type(exc).__name__)
        jobs[job_id]["status"] = "error"
        jobs[job_id]["step"] = "Processing failed"

        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job_record = result.scalar_one_or_none()
            if job_record and job_record.status == "error":
                # The per-clip render failure handler above already set the
                # error state, refunded the credit, and committed before
                # re-raising to unwind out of this function. Refunding again
                # here would grant the user a free credit per failed job.
                logger.debug(
                    "Skipping duplicate error handling for job %s (already marked error)",
                    job_id,
                )
            elif job_record:
                job_record.status = "error"
                job_record.error = "Processing failed"
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
    plan_obj = _get_platform_plan(user, platform)
    plan = plan_obj.value if hasattr(plan_obj, "value") else str(plan_obj)
    if (
        request.transcription_mode is TranscriptionMode.QUALITY
        and plan != "proplus"
    ):
        raise HTTPException(
            status_code=403,
            detail="QUALITY transcription requires a Pro+ plan",
        )

    await _reset_platform_counter_if_new_month(user, db, platform)
    # Serialize quota decisions for this user (same pattern as the Twitch
    # advanced route): without this lock, two concurrent /generate requests
    # both read the same pre-increment usage, both pass the check below, and
    # both increment — exceeding the plan's monthly limit. The counter reset
    # above commits independently; only the final check/consume/Job-create
    # transaction needs the row lock.
    locked_user = await db.scalar(
        select(User).where(User.id == user.id).with_for_update()
    )
    if locked_user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user = locked_user

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
            transcription_mode=request.transcription_mode,
            include_subtitles=request.include_subtitles,
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
    except subprocess.CalledProcessError:
        logger.warning("yt-dlp preview failed")
        raise HTTPException(status_code=400, detail="Unable to preview this video")
    except Exception as exc:
        logger.error("Unexpected error while previewing video: exception_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Unable to preview this video")


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
    except RuntimeError:
        logger.warning("Twitch API request failed for channel %s", channel_login)
        raise HTTPException(status_code=400, detail="Unable to fetch Twitch VODs")
    except Exception as exc:
        logger.error(
            "Unexpected error while fetching Twitch VODs: exception_type=%s",
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Unable to fetch Twitch VODs")


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_record = await job_access_service.require_owned_job(db, job_id, user)

    # Fast path: job still in memory
    memory_job = job_access_service.get_owned_memory_job(job_record, jobs)
    if memory_job is not None:
        raw_clips = memory_job.get("clips", []) or []
        normalized = public_clip_payloads(job_id, raw_clips)
        return StatusResponse(
            job_id=job_id,
            status=memory_job["status"],
            progress=memory_job["progress"],
            step=memory_job["step"],
            clips=normalized,
        )

    # Fallback: job lost from memory (container restart) — use the DB record.
    import json

    clips = json.loads(job_record.clips_json) if job_record.clips_json else []
    if job_record.status == "done":
        step = "done"
    elif job_record.status == "error":
        step = job_record.message or "Processing failed"
    else:
        # job_record.message carries the real, persisted pipeline step (e.g.
        # RQ workers write it incrementally) once available; otherwise fall
        # back to the raw status ("pending"/"processing").
        step = job_record.message or job_record.status
    progress = 100 if job_record.status == "done" else job_record.progress

    # Only cache a *terminal* result: a job still processing keeps changing
    # in the DB (RQ workers persist progress there — they never touch this
    # in-memory dict directly, being a separate OS process), and this fast
    # path never re-checks the DB once populated. Caching an in-progress
    # snapshot would freeze every later poll at that snapshot for the rest
    # of the job's run.
    if job_record.status in ("done", "error"):
        jobs[job_id] = {
            "status": job_record.status,
            "progress": progress,
            "step": step,
            "clips": clips,
            "user_id": user.id,
        }
    normalized = public_clip_payloads(job_id, clips)
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

    job_record = await job_access_service.require_owned_job(db, job_id, user)
    memory_job = job_access_service.get_owned_memory_job(job_record, jobs)
    if memory_job is not None:
        return JSONResponse(
            {
                "clips": public_clip_payloads(job_id, memory_job.get("clips", [])),
                "video_title": memory_job.get("video_title"),
                "status": memory_job.get("status"),
            }
        )

    clips = json.loads(job_record.clips_json) if job_record.clips_json else []
    return JSONResponse(
        {
            "clips": public_clip_payloads(job_id, clips),
            "video_title": job_record.video_title,
            "status": job_record.status,
        }
    )


@router.get(
    "/jobs/{job_id}/clips/{clip_index}/media",
    operation_id="get_private_clip_media",
)
@router.head(
    "/jobs/{job_id}/clips/{clip_index}/media",
    operation_id="head_private_clip_media",
)
async def private_clip_media(job_id: str, clip_index: int, request: Request, download: bool = False, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = await job_access_service.require_owned_job(db, job_id, user)
    try:
        opened_clip = open_clip(settings.clips_dir, job.id, clip_at(job.clips_json, clip_index))
    except MediaNotFound:
        raise HTTPException(status_code=404, detail="Clip not found") from None
    size = opened_clip.size
    try:
        byte_range = parse_range(request.headers.get("range"), size)
    except InvalidRange:
        close_clip(opened_clip)
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"})
    start, end = byte_range if byte_range else (0, size - 1)
    headers = {"Accept-Ranges":"bytes", "Cache-Control":"private, no-store", "X-Content-Type-Options":"nosniff", "Content-Length":str(end-start+1), "Content-Disposition":f'{"attachment" if download else "inline"}; filename="{filename(opened_clip.name)}"'}
    status = 206 if byte_range else 200
    if byte_range: headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    if request.method == "HEAD":
        close_clip(opened_clip)
        return Response(status_code=status, headers=headers, media_type=media_type(opened_clip.name))
    return _PrivateMediaStreamingResponse(opened_clip, start, end, status_code=status, headers=headers, media_type=media_type(opened_clip.name))


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
                "clips_url": f"/api/status/{j.id}",
                "hashtags": hashtags,
            }
        )

    return JSONResponse({"history": history})


# ── Development-only diagnostics ────────────────────────────────────────────
if settings.is_development:

    @router.get("/debug/job/{job_id}")
    async def debug_job(
        job_id: str,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Return owned job state for local troubleshooting only."""
        job_record = await job_access_service.require_owned_job(db, job_id, user)
        in_memory = job_access_service.get_owned_memory_job(job_record, jobs)
        safe_memory = dict(in_memory) if in_memory is not None else None
        if safe_memory is not None:
            safe_memory["clips"] = public_clip_payloads(
                job_id, safe_memory.get("clips", [])
            )
        db_row = {
            "id": job_record.id,
            "status": job_record.status,
            "progress": job_record.progress,
            "video_title": job_record.video_title,
            "error": job_record.error,
            "clips": public_clip_payloads(job_id, job_record.clips_json),
            "created_at": job_record.created_at.isoformat()
            if job_record.created_at
            else None,
        }

        return JSONResponse({"in_memory": safe_memory, "db": db_row})
