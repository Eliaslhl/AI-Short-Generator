"""
worker.py – Worker tasks for async video processing.

Handles:
- Video download
- Segmentation (chunking)
- Highlight detection
- Clip generation
"""

import logging
from typing import Dict, Any, Optional, List

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
        ctx.update_progress(10, "Downloading video from Twitch...")
        video_path = _download_twitch_video(video_url, job_id)
        if not video_path:
            raise Exception("Failed to download video from Twitch")
        
        logger.info(f"✅ Video downloaded: {video_path}")
        ctx.update_progress(20, "Segmenting video into chunks...")
        chunks = _segment_video(video_url, chunk_duration)
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
        clips = _generate_clips(best_highlights, video_path, max_clips)
        ctx.clips = clips
        
        ctx.update_progress(95, "Finalizing...")
        
        return {
            "success": True,
            "job_id": job_id,
            "progress": 100,
            "step": "Complete!",
            "clips": [c for c in ctx.clips if c],
            "errors": ctx.errors,
        }
    
    except Exception as e:
        logger.exception(f"❌ Error processing job {job_id}: {e}")
        ctx.add_error(str(e))
        return {
            "success": False,
            "job_id": job_id,
            "progress": ctx.progress,
            "step": ctx.step,
            "error": str(e),
            "errors": ctx.errors,
        }


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
        
        if not duration:
            logger.error(f"❌ Could not determine video duration")
            return []
        
        # Calculate number of chunks
        num_chunks = max(1, int(duration / chunk_duration))
        chunks = []
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            # Last chunk might be shorter
            chunk_dur = min(chunk_duration, duration - start_time)
            
            chunk_id = f"{i:03d}"
            chunk_path = f"/tmp/chunk_{chunk_id}.mp4"
            
            chunks.append({
                "chunk_id": chunk_id,
                "start_time": start_time,
                "duration": chunk_dur,
                "path": chunk_path,
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
        
        # Download video
        output_path = f"/tmp/{job_id}_vod.mp4"
        video_path = download_manager.download_twitch_vod(
            video_url=video_url,
            vod_id=parsed.get("id", job_id),
            output_path=output_path,
        )
        
        return video_path
        
    except Exception as e:
        logger.error(f"❌ Error downloading Twitch video: {e}")
        return None


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
        generator = create_clip_generator(output_dir="/tmp/clips")
        
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
                        "formats": {
                            "mp4": clip_paths.get("mp4"),
                            "webm": clip_paths.get("webm"),
                        },
                        "file": clip_paths.get("mp4"),  # Primary format
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


# Register with queue system
def register_workers():
    """Register worker tasks with the queue system."""
    queue = get_queue()
    
    # This would be used by Celery or similar
    # For RQ, tasks are registered automatically via function reference
    logger.info("✅ Workers registered")
