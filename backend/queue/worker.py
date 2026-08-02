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
import os
import shutil
import stat
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Any, Optional, List

from sqlalchemy import select

from backend.security_logging import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

_TIMESTAMP_TOLERANCE_SECONDS = 0.001

# Import queue and services
from backend.queue.redis_queue import get_queue
from backend.services.highlight_detector import HighlightDetector, HighlightSegment
from backend.services.audio_processor import process_audio_for_highlight_detection
from backend.services.motion_processor import process_video_for_motion_detection
from backend.services.twitch_client import (
    TwitchClient, VideoDownloadManager, create_twitch_client, create_download_manager
)
from backend.services.clip_generator import ClipGenerator, create_clip_generator
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models.user import Job, User
from backend.api.routes import _decrement_platform_usage


@dataclass(frozen=True)
class TwitchDownloadedSource:
    """A worker-owned source path and the workspace that owns it."""

    path: str
    workspace: Path


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
    downloaded_source: Optional[TwitchDownloadedSource] = None
    
    try:
        if not asyncio.run(_begin_twitch_job(job_id, user_id)):
            return {
                "success": False,
                "job_id": job_id,
                "error": "Job is not available for processing",
            }
        ctx.update_progress(10, "Downloading video from Twitch...")
        downloaded = _download_twitch_video(video_url, job_id)
        if not downloaded:
            raise Exception("Failed to download video from Twitch")
        if isinstance(downloaded, TwitchDownloadedSource):
            if not _is_twitch_downloaded_source(downloaded.path, downloaded.workspace):
                raise ValueError("Downloaded Twitch source is outside its workspace")
            downloaded_source = downloaded
            video_path = str(_validate_downloaded_video(downloaded_source.path))
        else:
            # Preserve compatibility with test doubles and legacy private callers.
            # A bare path has no provable workspace ownership and is never deleted.
            video_path = str(_validate_downloaded_video(downloaded))
        
        logger.info("Twitch source downloaded: job_id=%s", job_id)
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
    finally:
        if downloaded_source is not None:
            _cleanup_twitch_download_workspace(downloaded_source.workspace, job_id)


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
                "source_duration": duration,
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
) -> Optional[TwitchDownloadedSource]:
    """
    Download a Twitch video by URL or parse and download by VOD ID.
    
    Args:
        video_url: Twitch URL or VOD ID
        job_id: Job ID for naming
    
    Returns:
        Path to downloaded video or None
    """
    workspace: Optional[Path] = None
    try:
        twitch = create_twitch_client()
        download_manager = create_download_manager()
        
        # Parse URL to extract VOD ID
        parsed = twitch.parse_twitch_url(video_url)
        
        if not parsed:
            logger.error("Could not parse Twitch URL: job_id=%s", job_id)
            return None
        
        if parsed["type"] == "vod":
            vod_id = parsed["id"]
            # Reconstruct full URL if only ID was provided
            if not video_url.startswith("http"):
                video_url = f"https://www.twitch.tv/videos/{vod_id}"
        else:
            logger.error(f"❌ URL is not a VOD: {parsed['type']}")
            return None
        
        # Each attempt gets a dedicated workspace under the configured temporary
        # root. Final clips are written separately below ``clips_dir/<job_id>``.
        workspace = _create_twitch_download_workspace()
        output_path = workspace / "source.mp4"
        video_path = download_manager.download_twitch_vod(
            video_url=video_url,
            vod_id=parsed.get("id", job_id),
            output_path=str(output_path),
        )
        
        if not video_path or not _is_twitch_downloaded_source(video_path, workspace):
            _cleanup_twitch_download_workspace(workspace, job_id)
            return None

        return TwitchDownloadedSource(path=video_path, workspace=workspace)
        
    except Exception as exc:
        if workspace is not None:
            _cleanup_twitch_download_workspace(workspace, job_id)
        logger.error(
            "Twitch source download failed: job_id=%s exception_type=%s",
            job_id,
            type(exc).__name__,
        )
        return None


def _twitch_download_temp_root() -> Path:
    """Return the controlled root reserved for worker-owned Twitch sources."""
    return Path(settings.video_temp_dir) / "twitch-downloads"


def _create_twitch_download_workspace() -> Path:
    """Create one collision-free workspace for a single worker download attempt."""
    root = _twitch_download_temp_root()
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / uuid.uuid4().hex
    workspace.mkdir()
    return workspace


def _is_twitch_download_workspace(workspace: Path) -> bool:
    """Accept only a real, direct child of the controlled Twitch temp root."""
    try:
        root = _twitch_download_temp_root().resolve(strict=False)
        parent = workspace.parent.resolve(strict=False)
        workspace_stat = workspace.lstat()
    except (OSError, ValueError):
        return False
    return parent == root and stat.S_ISDIR(workspace_stat.st_mode) and not workspace.is_symlink()


def _is_twitch_downloaded_source(source_path: str | Path, workspace: Path) -> bool:
    """Return whether a source is a direct, non-symlink file in this workspace."""
    candidate = Path(source_path)
    try:
        source_stat = candidate.lstat()
    except OSError:
        return False
    return (
        candidate.parent == workspace
        and _is_twitch_download_workspace(workspace)
        and stat.S_ISREG(source_stat.st_mode)
        and not candidate.is_symlink()
    )


def _cleanup_twitch_download_workspace(workspace: Path, job_id: str) -> None:
    """Best-effort cleanup of a verified worker-created download workspace."""
    if not _is_twitch_download_workspace(workspace):
        return
    root_fd: Optional[int] = None
    workspace_fd: Optional[int] = None
    try:
        root = _twitch_download_temp_root().resolve(strict=False)
        open_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
        root_fd = os.open(root, open_flags)
        workspace_fd = os.open(workspace.name, open_flags, dir_fd=root_fd)
        workspace_stat = os.fstat(workspace_fd)
        if not stat.S_ISDIR(workspace_stat.st_mode):
            return
        for entry_name in os.listdir(workspace_fd):
            entry_stat = os.lstat(entry_name, dir_fd=workspace_fd)
            if stat.S_ISREG(entry_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode):
                os.unlink(entry_name, dir_fd=workspace_fd)
        current_stat = os.stat(workspace.name, dir_fd=root_fd, follow_symlinks=False)
        if (current_stat.st_dev, current_stat.st_ino) != (
            workspace_stat.st_dev,
            workspace_stat.st_ino,
        ):
            return
        os.rmdir(workspace.name, dir_fd=root_fd)
    except FileNotFoundError:
        return
    except OSError as exc:
        logger.warning(
            "Twitch temporary source cleanup failed: job_id=%s exception_type=%s",
            job_id,
            type(exc).__name__,
        )
    finally:
        for file_descriptor in (workspace_fd, root_fd):
            if file_descriptor is None:
                continue
            try:
                os.close(file_descriptor)
            except OSError as exc:
                logger.warning(
                    "Twitch temporary source cleanup failed: job_id=%s exception_type=%s",
                    job_id,
                    type(exc).__name__,
                )




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
    chunk_id = chunk.get("chunk_id", "unknown")
    video_path = chunk.get("path")
    chunk_start = _finite_number(chunk.get("start_time", 0.0), "chunk start_time")
    chunk_duration = _finite_number(chunk.get("duration"), "chunk duration")
    if chunk_start < 0 or chunk_duration <= 0:
        raise ValueError("Twitch chunk has invalid timing")
    if not isinstance(video_path, str) or not Path(video_path).is_file():
        raise ValueError("Twitch chunk source is unavailable")

    source_duration = chunk.get("source_duration")
    if source_duration is not None:
        source_duration = _finite_number(source_duration, "source duration")
        if source_duration <= 0 or (
            chunk_start + chunk_duration
            > source_duration + _TIMESTAMP_TOLERANCE_SECONDS
        ):
            raise ValueError("Twitch chunk exceeds its source duration")

    try:
        # The module functions intentionally provide high-level processing.
        # Both receive the same source window and return chunk-local data.
        audio_features = process_audio_for_highlight_detection(
            video_path,
            sample_rate=22050,
            start_time=chunk_start,
            duration=chunk_duration,
        )
        motion_features = process_video_for_motion_detection(
            video_path,
            fps=30,
            start_time=chunk_start,
            duration=chunk_duration,
        )
        audio_data = audio_features.get("audio")
        frame_diffs = motion_features.get("frame_differences", [])
        if hasattr(frame_diffs, "tolist"):
            frame_diffs = frame_diffs.tolist()
        else:
            frame_diffs = list(frame_diffs)
        motion_fps = _finite_number(
            motion_features.get("analysis_fps", 30.0), "motion analysis fps"
        )
        if motion_fps <= 0:
            raise ValueError("Twitch motion analysis has invalid FPS")
        logger.info(
            "Twitch chunk analysis completed: chunk_id=%s audio_samples=%s motion_frames=%s",
            chunk_id,
            len(audio_data) if audio_data is not None else 0,
            len(frame_diffs),
        )

        detector = HighlightDetector(language=language)
        highlights = detector.detect_highlights(
            audio_data=audio_data,
            frame_diffs=frame_diffs,
            transcription="",  # TODO: Add speech-to-text
            segment_duration=chunk_duration,
            motion_fps=motion_fps,
        )
        global_highlights = [
            _offset_highlight(highlight, chunk_start, chunk_duration, source_duration)
            for highlight in highlights
        ]
        logger.info(
            "Twitch chunk highlights detected: chunk_id=%s count=%s",
            chunk_id,
            len(global_highlights),
        )
        return global_highlights
    except Exception as exc:
        logger.error(
            "Twitch chunk analysis failed: chunk_id=%s exception_type=%s",
            chunk_id,
            type(exc).__name__,
        )
        raise RuntimeError("Twitch chunk analysis failed") from exc


def _finite_number(value: Any, field_name: str) -> float:
    """Return a finite timestamp-like value or reject malformed worker input."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


def _offset_highlight(
    highlight: HighlightSegment,
    chunk_start: float,
    chunk_duration: float,
    source_duration: Optional[float] = None,
) -> HighlightSegment:
    """Copy one chunk-local highlight into the source's global timeline."""
    local_start = _finite_number(highlight.start_time, "highlight start_time")
    local_end = _finite_number(highlight.end_time, "highlight end_time")
    if local_start < 0 or local_end <= local_start:
        raise ValueError("Twitch highlight has invalid timing")
    if local_end > chunk_duration + _TIMESTAMP_TOLERANCE_SECONDS:
        raise ValueError("Twitch highlight exceeds its chunk duration")

    global_start = chunk_start + local_start
    global_end = chunk_start + local_end
    if source_duration is not None:
        if global_end > source_duration + _TIMESTAMP_TOLERANCE_SECONDS:
            raise ValueError("Twitch highlight exceeds its source duration")
        global_end = min(global_end, source_duration)
    if global_end <= global_start:
        raise ValueError("Twitch highlight has invalid global timing")
    return replace(highlight, start_time=global_start, end_time=global_end)


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
        # A hard kill mid-generation (OOM, deploy) can strand a generator
        # scratch directory before its own `finally` cleanup runs. Sweep
        # leftovers from a prior attempt before starting a new one.
        for stale_scratch in output_dir.glob(".clipgen-scratch-*"):
            if stale_scratch.is_dir() and not stale_scratch.is_symlink():
                shutil.rmtree(stale_scratch, ignore_errors=True)
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
                clip_id = f"clip_{idx:03d}"

                # Generate with effects. Only "mp4" is ever consumed downstream;
                # requesting other formats here would produce and immediately
                # discard files nobody reads.
                clip_paths = generator.generate_from_highlight(
                    video_path=video_path,
                    highlight=highlight_dict,
                    apply_effects=True,
                    output_formats=["mp4"],
                    clip_id=clip_id,
                )

                if clip_paths.get("mp4"):
                    clip_info = {
                        "clip_id": clip_id,
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
