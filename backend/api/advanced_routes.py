"""
advanced_routes.py – API endpoints for advanced Twitch video processing.

Routes:
POST /api/generate/twitch/advanced – Start advanced processing
GET  /api/status/twitch/{job_id} – Get detailed job status
"""

import logging
import uuid
from typing import Dict, Any
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.models.user import Job, User
from backend.queue.redis_queue import get_queue
from backend.queue.worker import process_twitch_video
from backend.services.job_access_service import job_access_service
from backend.services.private_media_service import public_clip_payloads
from backend.api.routes import (
    _decrement_platform_usage,
    _get_platform_limit,
    _get_platform_plan,
    _get_platform_usage,
    _increment_platform_usage,
    _reset_platform_counter_if_new_month,
)

logger = logging.getLogger(__name__)
advanced_router = APIRouter()


def _is_twitch_vod_url(value: str) -> bool:
    """Accept only canonical Twitch VOD URLs supported by the worker."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    hostname = (parsed.hostname or "").lower().rstrip(".")
    parts = parsed.path.rstrip("/").split("/")
    return (
        parsed.scheme in {"http", "https"}
        and hostname in {"twitch.tv", "www.twitch.tv"}
        and parsed.username is None
        and parsed.password is None
        and port in {None, 80 if parsed.scheme == "http" else 443}
        and not parsed.query
        and not parsed.fragment
        and len(parts) == 3
        and parts[0] == ""
        and parts[1] == "videos"
        and parts[2].isdigit()
    )


class TwitchAdvancedRequest(BaseModel):
    """Request for advanced Twitch video processing."""
    url: str
    max_clips: int = Field(default=5, ge=1, le=20)
    language: str = "en"


class TwitchAdvancedResponse(BaseModel):
    """Response for advanced Twitch video processing."""
    job_id: str
    status: str
    progress: int
    step: str


class TwitchStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str
    status: str
    progress: int
    step: str
    clips: list = []
    error: str | None = None


@advanced_router.post("/generate/twitch/advanced", response_model=TwitchAdvancedResponse)
async def generate_twitch_advanced(
    req: TwitchAdvancedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Start advanced Twitch video processing with chunking and highlighting.
    
    Features:
    - Intelligent chunking (30-minute segments)
    - Parallel highlight detection
    - Scoring algorithm (audio + motion + text)
    - Real-time progress updates
    
    Args:
        req: Processing request
        current_user: Authenticated user
    
    Returns:
        Job info with ID for status polling
    """
    logger.info("Starting advanced Twitch processing for user %s", current_user.id)
    
    # Validate URL
    if not _is_twitch_vod_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid Twitch URL")

    platform = "twitch"
    await _reset_platform_counter_if_new_month(current_user, db, platform)
    # Serialize quota decisions for this user on PostgreSQL. The counter reset
    # commits independently, so acquire the row lock only for the final check,
    # consumption, and Job creation transaction below.
    locked_user = await db.scalar(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    if locked_user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    current_user = locked_user
    usage = _get_platform_usage(current_user, platform)
    limit = _get_platform_limit(current_user, platform)
    if usage >= limit:
        plan_obj = _get_platform_plan(current_user, platform)
        plan_name = plan_obj.value if hasattr(plan_obj, "value") else str(plan_obj)
        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "message": (
                    f"You've used all {limit} of your {plan_name} plan generations "
                    "this month for Twitch."
                ),
                "platform": platform,
                "limit": limit,
                "used": usage,
                "upgrade_url": "/pricing",
            },
        )
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    job = Job(
        id=job_id,
        user_id=current_user.id,
        youtube_url=req.url,
        status="pending",
        progress=0,
    )
    db.add(job)
    _increment_platform_usage(current_user, platform)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error("Failed to persist Twitch job: job_id=%s", job_id)
        raise HTTPException(status_code=500, detail="Failed to start processing")

    queue = get_queue()
    try:
        queue.enqueue(
            process_twitch_video,
            job_id,
            str(current_user.id),
            req.url,
            job_id=job_id,
            meta={"user_id": current_user.id},
            max_clips=req.max_clips,
            language=req.language,
        )
        
        logger.info("Enqueued advanced Twitch job %s", job_id)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "step": "Queued for processing...",
        }
    
    except Exception as exc:
        await db.delete(job)
        _decrement_platform_usage(current_user, platform)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        logger.error(
            "Failed to enqueue advanced Twitch job: exception_type=%s",
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Failed to start processing")


@advanced_router.get("/status/twitch/{job_id}", response_model=TwitchStatusResponse)
async def get_twitch_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed status of a Twitch processing job.
    
    Includes:
    - Current progress (0-100%)
    - Current step/phase
    - Generated clips (when ready)
    - Error messages (if failed)
    
    Args:
        job_id: Job ID
        current_user: Authenticated user
    
    Returns:
        Detailed job status
    """
    queue = get_queue()

    try:
        job_access_service.require_owned_rq_job(queue, job_id, current_user)
        status = queue.get_job_status(job_id)

        return {
            "job_id": job_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "step": status.get("step", "Processing..."),
            "clips": public_clip_payloads(
                job_id,
                status.get("result", {}).get("clips", [])
                if status.get("status") == "finished"
                else [],
            ),
            "error": status.get("error"),
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to get advanced Twitch job status: exception_type=%s",
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Failed to get job status")


@advanced_router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Cancel a processing job.
    
    Args:
        job_id: Job ID to cancel
        current_user: Authenticated user
    
    Returns:
        Cancellation result
    """
    queue = get_queue()

    try:
        job_access_service.require_owned_rq_job(queue, job_id, current_user)
        success = queue.cancel_job(job_id)

        if success:
            logger.info(f"❌ Cancelled job {job_id}")
            return {"status": "cancelled", "job_id": job_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to cancel advanced Twitch job: exception_type=%s",
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="Failed to cancel job")
