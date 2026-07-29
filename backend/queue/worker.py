"""
worker.py – Worker tasks for async video processing.

Handles:
- Video download
- Segmentation (chunking)
- Highlight detection
- Clip generation
"""

import asyncio
import json
import logging
import math
from pathlib import Path
from typing import Dict, Any, Optional, List

from sqlalchemy import select

from backend.security_logging import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

# Import queue and services
from backend.queue.redis_queue import get_queue
from backend.services.highlight_detector import HighlightDetector, HighlightSegment
from backend.services.audio_processor import RealAudioProcessor
from backend.services.motion_processor import MotionProcessor
from backend.services.twitch_client import (
    TwitchClient, VideoDownloadManager, create_twitch_client, create_download_manager
)
from backend.services.clip_generator import ClipGenerator, create_clip_generator
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models.user import Job, User
from backend.api.routes import _decrement_platform_usage


class ProcessingContext:
    """Context for a processing job."""
    
    def __init__(self, job_id: str, user_id: str):
        self.job_id = job_id
        self.user_id = user_id
        self.progress = 0
        self.step = "Initializing..."
        self.chunks: List[Dict[str, Any]] = []
        self.highlights: List[HighlightSegment] = []
        self.clips: List[Dict[str, Any]] = []
        self.errors: List[str] = []
    
    def update_progress(self, progress: int, step: str):
        """Update job progress."""
        self.progress = min(progress, 100)
        self.step = step
        logger.info(f"📊 [{self.job_id}] {progress}% - {step}")
    
    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(error)
        logger.error(f"❌ [{self.job_id}] {error}")


def process_twitch_video(
    job_id: str,
    user_id: str,
    video_url: str,
    max_clips: int = 5,
    language: str = "en",
    chunk_duration: int = 30 * 60,  # 30 minutes
) -> Dict[str, Any]:
    """
    Main worker task to process a Twitch video.
    
    Args:
        job_id: unique job identifier
        user_id: user ID
        video_url: Twitch video URL
        max_clips: maximum clips to generate
        language: transcription language
        chunk_duration: duration of each chunk in seconds
    
    Returns:
        Processing result
    """
    ctx = ProcessingContext(job_id, user_id)
    
    try:
        if not asyncio.run(_begin_twitch_job(job_id, user_id)):
            return {
                "success": False,
                "job_id": job_id,
                "error": "Job is not available for processing",
            }
        ctx.update_progress(10, "Downloading video from Twitch...")
        video_path = _download_twitch_video(video_url, job_id)
        if not video_path:
            raise Exception("Failed to download video from Twitch")
        video_path = str(_validate_downloaded_video(video_path))
        
        logger.info(f"✅ Video downloaded: {video_path}")
        ctx.update_progress(20, "Segmenting video into chunks...")
        chunks = _segment_video(video_path, chunk_duration)
        if not chunks:
            raise RuntimeError("Unable to segment downloaded video")
        ctx.chunks = chunks
        logger.info(f"✅ Segmented into {len(chunks)} chunks")
        
        ctx.update_progress(30, "Processing chunks...")
        for idx, chunk in enumerate(chunks):
            chunk_progress = 30 + (idx / len(chunks)) * 40  # 30-70%
            ctx.update_progress(
                int(chunk_progress),
                f"Processing chunk {idx + 1}/{len(chunks)}...",
            )
            
            # Process each chunk
            highlights = _process_chunk(chunk, language)
            ctx.highlights.extend(highlights)
        
        ctx.update_progress(75, "Filtering and merging highlights...")
        best_highlights = _filter_highlights(ctx.highlights, max_clips)
        
        ctx.update_progress(85, "Generating clips...")
        clips = _generate_clips(best_highlights, video_path, job_id, max_clips)
        clips = _validate_generated_clips(clips, job_id)
        if not clips:
            raise RuntimeError("No clips were generated")
        ctx.clips = clips

        ctx.update_progress(95, "Finalizing...")
        asyncio.run(_persist_twitch_job_result(job_id, clips, "done", 100))
        
        return {
            "success": True,
            "job_id": job_id,
            "progress": 100,
            "step": "Complete!",
            "clips": [c for c in ctx.clips if c],
            "errors": ctx.errors,
        }
    
    except Exception as exc:
        logger.error(
            "Error processing job: job_id=%s exception_type=%s",
            job_id,
            type(exc).__name__,
        )
        ctx.add_error("Processing failed")
        try:
            asyncio.run(
                _persist_twitch_job_result(
                    job_id, [], "error", ctx.progress, "Processing failed", refund_quota=True
                )
            )
        except Exception:
            logger.exception("Failed to persist Twitch job failure: job_id=%s", job_id)
        # RQ must see a failed execution. Returning an error dictionary marks the
        # RQ job as finished and makes polling contradict the persisted Job state.
        raise RuntimeError("Twitch processing failed") from exc


def _segment_video(
    video_path: str,
    chunk_duration: int,
) -> List[Dict[str, Any]]:
    """
    Segment a video into chunks.
    
    Args:
        video_path: Path to downloaded video file
        chunk_duration: duration per chunk in seconds
    
    Returns:
        List of chunk metadata
    """
    try:
        # Get video duration
        download_manager = create_download_manager()
        duration = download_manager.get_video_duration(video_path)
        
        if not duration or duration <= 0:
            logger.error(f"❌ Could not determine video duration")
            return []
        
        # Calculate number of chunks
        num_chunks = max(1, math.ceil(duration / chunk_duration))
        chunks = []
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            # Last chunk might be shorter
            chunk_dur = min(chunk_duration, duration - start_time)
            
            chunk_id = f"{i:03d}"
            chunks.append({
                "chunk_id": chunk_id,
                "start_time": start_time,
                "duration": chunk_dur,
                # Processors receive the downloaded local video, never the Twitch URL.
                # Chunk timing remains metadata for the highlight detector and renderer.
                "path": video_path,
                "original_video": video_path,
            })
        
        logger.info(f"✅ Segmented video into {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Error segmenting video: {e}")
        return []


def _download_twitch_video(
    video_url: str,
    job_id: str,
) -> Optional[str]:
    """
    Download a Twitch video by URL or parse and download by VOD ID.
    
    Args:
        video_url: Twitch URL or VOD ID
        job_id: Job ID for naming
    
    Returns:
        Path to downloaded video or None
    """
    try:
        twitch = create_twitch_client()
        download_manager = create_download_manager()
        
        # Parse URL to extract VOD ID
        parsed = twitch.parse_twitch_url(video_url)
        
        if not parsed:
            logger.error(f"❌ Could not parse Twitch URL: {video_url}")
            return None
        
        if parsed["type"] == "vod":
            vod_id = parsed["id"]
            # Reconstruct full URL if only ID was provided
            if not video_url.startswith("http"):
                video_url = f"https://www.twitch.tv/videos/{vod_id}"
        else:
            logger.error(f"❌ URL is not a VOD: {parsed['type']}")
            return None
        
        # Keep downloads in a job-scoped, controlled workspace. Final clips are
        # written separately below ``clips_dir/<job_id>``.
        output_dir = Path(settings.clips_dir).parent / "twitch-downloads" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "source.mp4"
        video_path = download_manager.download_twitch_vod(
            video_url=video_url,
            vod_id=parsed.get("id", job_id),
            output_path=str(output_path),
        )
        
        return video_path
        
    except Exception as e:
        logger.error(f"❌ Error downloading Twitch video: {e}")
        return None


def _validate_downloaded_video(video_path: str) -> Path:
    """Reject failed or non-video downloads before any local video processing."""
    path = Path(video_path)
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size <= 0
        or path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}
    ):
        raise ValueError("Downloaded Twitch video is invalid")
    return path


def _process_chunk(
    chunk: Dict[str, Any],
    language: str,
) -> List[HighlightSegment]:
    """
    Process a single chunk to detect highlights using real audio/motion analysis.
    
    Args:
        chunk: chunk metadata with path and timestamps
        language: transcription language
    
    Returns:
        List of highlights in chunk
    """
    detector = HighlightDetector(language=language)
    video_path = chunk["path"]
    
    try:
        # Extract real audio features
        audio_processor = RealAudioProcessor()
        audio_features = audio_processor.process_audio_for_highlight_detection(
            video_path=video_path,
            sr=22050,
            chunk_duration=chunk["duration"]
        )
        logger.info(f"✅ Extracted audio features: {len(audio_features.get('energy_scores', []))} frames")
        
        # Extract real motion features  
        motion_processor = MotionProcessor()
        motion_features = motion_processor.process_video_for_motion_detection(
            video_path=video_path,
            skip_frames=2,
            resize_frames=True
        )
        logger.info(f"✅ Extracted motion features: {len(motion_features.get('frame_diffs', []))} frames")
        
        # Use real data from processors
        highlights = detector.detect_highlights(
            audio_data=audio_features.get("energy_scores", []),
            frame_diffs=motion_features.get("frame_diffs", []),
            transcription="",  # TODO: Add speech-to-text
            segment_duration=chunk["duration"],
        )
        
        logger.info(f"🎯 Detected {len(highlights)} highlights in chunk")
        return highlights
        
    except Exception as e:
        logger.error(f"❌ Error processing chunk {chunk.get('chunk_id')}: {e}")
        # Return empty list instead of crashing
        return []


def _filter_highlights(
    highlights: List[HighlightSegment],
    max_clips: int,
) -> List[HighlightSegment]:
    """
    Filter and rank highlights to select top clips.
    
    Args:
        highlights: all detected highlights
        max_clips: maximum clips to keep
    
    Returns:
        Top highlights
    """
    # Sort by score
    sorted_highlights = sorted(highlights, key=lambda h: h.score, reverse=True)
    
    # Take top max_clips
    best = sorted_highlights[:max_clips]
    
    logger.info(f"🏆 Selected top {len(best)} highlights")
    return best


def _generate_clips(
    highlights: List[HighlightSegment],
    video_path: str,
    job_id: str,
    max_clips: int = 5,
) -> List[Dict[str, Any]]:
    """
    Generate actual clip files from highlights using FFmpeg.
    
    Args:
        highlights: selected highlights
        video_path: path to source video file
        max_clips: maximum clips to generate
    
    Returns:
        List of generated clip metadata
    """
    clips = []
    
    try:
        output_dir = Path(settings.clips_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        # RQ may retry a job. Remove deterministic prior outputs so persisted
        # metadata can never mix clips from two attempts.
        for prior_clip in output_dir.glob("clip_*"):
            if prior_clip.is_file() or prior_clip.is_symlink():
                prior_clip.unlink()
        generator = create_clip_generator(output_dir=str(output_dir))
        
        # Generate clips from highlights
        for idx, highlight in enumerate(highlights[:max_clips]):
            try:
                logger.info(f"🎬 Generating clip {idx + 1}/{len(highlights[:max_clips])}")
                
                # Create clip data dict for generator
                highlight_dict = {
                    "start_time": highlight.start_time,
                    "end_time": highlight.end_time,
                    "score": highlight.score,
                }
                
                # Generate with effects and multiple formats
                clip_paths = generator.generate_from_highlight(
                    video_path=video_path,
                    highlight=highlight_dict,
                    apply_effects=True,
                    output_formats=["mp4", "webm"]
                )
                
                if clip_paths.get("mp4"):
                    clip_info = {
                        "clip_id": f"clip_{idx:03d}",
                        "start_time": highlight.start_time,
                        "end_time": highlight.end_time,
                        "duration": highlight.end_time - highlight.start_time,
                        "score": highlight.score,
                        "file": Path(clip_paths["mp4"]).name,
                    }
                    clips.append(clip_info)
                    logger.info(f"✅ Clip {idx + 1} generated successfully")
                else:
                    logger.error(f"❌ Failed to generate clip {idx + 1}")
            
            except Exception as e:
                logger.error(f"❌ Error generating clip {idx + 1}: {e}")
                continue
        
        logger.info(f"✂️ Generated {len(clips)}/{len(highlights[:max_clips])} clips successfully")
        return clips
    
    except Exception as e:
        logger.error(f"❌ Error in clip generation: {e}")
        return []


def _validate_generated_clips(clips: List[Dict[str, Any]], job_id: str) -> List[Dict[str, Any]]:
    """Keep only non-empty, job-local clip files safe to persist in ``clips_json``."""
    job_root = (Path(settings.clips_dir) / job_id).resolve()
    validated: List[Dict[str, Any]] = []
    for clip in clips:
        reference = clip.get("file") if isinstance(clip, dict) else None
        if (
            not isinstance(reference, str)
            or Path(reference).name != reference
            or reference.startswith(".")
            or any(character in reference for character in ("\\", ":", "\r", "\n", "\x00"))
        ):
            continue
        candidate = (job_root / reference).resolve()
        try:
            candidate.relative_to(job_root)
        except ValueError:
            continue
        if candidate.is_file() and not candidate.is_symlink() and candidate.stat().st_size > 0:
            validated.append(clip)
    return validated


async def _begin_twitch_job(job_id: str, user_id: str) -> bool:
    """Atomically reserve a pending job for one worker invocation."""
    async with AsyncSessionLocal() as session:
        job = await session.scalar(
            select(Job).where(Job.id == job_id).with_for_update()
        )
        if job is None or job.user_id != user_id or job.status != "pending":
            return False
        job.status = "processing"
        job.progress = 0
        job.error = None
        job.clips_json = json.dumps([])
        await session.commit()
        return True


async def _persist_twitch_job_result(
    job_id: str,
    clips: List[Dict[str, Any]],
    status: str,
    progress: int,
    error: str | None = None,
    refund_quota: bool = False,
) -> None:
    """Persist RQ output so the normal ownership and media route can serve it."""
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            logger.warning("Twitch job was not persisted: job_id=%s", job_id)
            return
        if refund_quota and job.status == "processing":
            user = await session.get(User, job.user_id)
            if user is not None:
                _decrement_platform_usage(user, "twitch")
        job.clips_json = json.dumps(clips)
        job.status = status
        job.progress = progress
        job.error = error
        await session.commit()


# Register with queue system
def register_workers():
    """Register worker tasks with the queue system."""
    queue = get_queue()
    
    # This would be used by Celery or similar
    # For RQ, tasks are registered automatically via function reference
    logger.info("✅ Workers registered")
