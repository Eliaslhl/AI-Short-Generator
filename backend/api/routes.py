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
from backend.auth.dependencies import get_current_user, require_can_generate
from backend.services.youtube_service import download_video, _get_cookies_file
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

    def update(progress: int, step: str):
        jobs[job_id]["progress"] = progress
        jobs[job_id]["step"] = step
        logger.info(f"[{job_id}] {progress}% – {step}")

    try:
        jobs[job_id]["status"] = "processing"

        update(5, "Downloading video from YouTube…")
        video_path, video_title = await asyncio.to_thread(
            download_video, youtube_url, job_id
        )
        jobs[job_id]["video_title"] = video_title

        update(20, "Transcribing audio with Faster-Whisper…")
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

        update(40, "Analysing and scoring segments…")
        top_segments = await asyncio.to_thread(
            select_top_segments, segments, max_clips, video_duration
        )
        # Ensure clips are rendered in chronological order (video timeline order)
        # so the generated shorts follow the source video sequence instead of
        # the ranking order returned by select_top_segments.
        top_segments.sort(key=lambda s: s.get("start", 0.0))

        update(55, "Generating viral hooks with local LLM…")
        for seg in top_segments:
            seg["hook"] = await asyncio.to_thread(generate_hook, seg["text"])

        # Pro+ only: auto title + auto hashtags
        if is_proplus:
            update(60, "Generating titles & hashtags (Pro+)…")
            for seg in top_segments:
                seg["ai_title"] = await asyncio.to_thread(generate_title, seg["text"])
                seg["hashtags"] = await asyncio.to_thread(
                    generate_hashtags, seg["text"]
                )

        update(65, "Building emoji captions…")
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
            update(pct, f"Rendering clip {idx + 1}/{total}…")
            clip_info = await asyncio.to_thread(
                render_clip,
                video_path=str(video_path),
                segment=seg,
                job_id=job_id,
                clip_index=idx,
                subtitle_style=subtitle_style,
            )
            clips.append(clip_info)

        update(100, "All clips are ready!")
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
                if user_record and user_record.generations_this_month > 0:
                    user_record.generations_this_month -= 1
                    logger.info(
                        f"Refunded generation credit for user {user_id} (job {job_id} failed)"
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
    user: User = Depends(require_can_generate),
    db: AsyncSession = Depends(get_db),
):
    """Start a generation job. Requires auth + quota check."""
    job_id = str(uuid.uuid4())[:8]

    # Enforce max_clips per plan server-side
    plan = user.plan.value
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
    user.generations_this_month += 1
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

    background_tasks.add_task(
        run_pipeline,
        job_id,
        request.youtube_url,
        user.id,
        allowed_clips,
        language,
        subtitle_style,
        plan == "proplus",
    )
    return GenerateResponse(job_id=job_id, message="Job started.")


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
        return StatusResponse(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            step=job["step"],
            clips=job.get("clips", []),
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
    return StatusResponse(
        job_id=job_id,
        status=job_record.status,
        progress=progress,
        step=step,
        clips=clips,
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
