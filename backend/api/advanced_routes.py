"""
advanced_routes.py – API endpoints for advanced Twitch video processing.

Routes:
POST /api/generate/twitch/advanced – Start advanced processing
GET  /api/status/twitch/{job_id} – Get detailed job status
"""

import logging
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.task_queue.redis_queue import get_queue
from backend.task_queue.worker import process_twitch_video

logger = logging.getLogger(__name__)
advanced_router = APIRouter()


class TwitchAdvancedRequest(BaseModel):
    """Request for advanced Twitch video processing."""
    url: str
    max_clips: int = 5
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
    error: str = None


@advanced_router.post("/api/generate/twitch/advanced", response_model=TwitchAdvancedResponse)
async def generate_twitch_advanced(
    req: TwitchAdvancedRequest,
    current_user: User = Depends(get_current_user),
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
    logger.info(f"🚀 Starting advanced Twitch processing for user {current_user.id}")
    
    # Validate URL
    if not req.url or "twitch.tv" not in req.url:
        raise HTTPException(status_code=400, detail="Invalid Twitch URL")
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Enqueue job
    queue = get_queue()
    try:
        queue.enqueue(
            process_twitch_video,
            job_id=job_id,
            args=(job_id, str(current_user.id), req.url),
            kwargs={
                "max_clips": req.max_clips,
                "language": req.language,
            },
        )
        
        logger.info(f"📨 Enqueued job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "step": "Queued for processing...",
        }
    
    except Exception as e:
        logger.exception(f"❌ Failed to enqueue job: {e}")
        raise HTTPException(status_code=500, detail="Failed to start processing")


@advanced_router.get("/api/status/twitch/{job_id}", response_model=TwitchStatusResponse)
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
        status = queue.get_job_status(job_id)
        
        return {
            "job_id": job_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "step": status.get("step", "Processing..."),
            "clips": status.get("result", {}).get("clips", []) if status.get("status") == "finished" else [],
            "error": status.get("error"),
        }
    
    except Exception as e:
        logger.exception(f"❌ Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@advanced_router.delete("/api/jobs/{job_id}")
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
        success = queue.cancel_job(job_id)
        
        if success:
            logger.info(f"❌ Cancelled job {job_id}")
            return {"status": "cancelled", "job_id": job_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")
    
    except Exception as e:
        logger.exception(f"❌ Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")
