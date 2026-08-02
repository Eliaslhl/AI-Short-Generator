"""
clip_generator.py – FFmpeg-based clip generation for highlights.

Handles:
- Video extraction from timestamps
- Audio extraction and mixing
- Effect application (transitions, overlays)
- Multi-format export (MP4, WebM, GIF)
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegConfig:
    """FFmpeg configuration and settings."""
    
    # Video codec settings
    VIDEO_CODEC = "libx264"
    VIDEO_PRESET = "medium"  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    VIDEO_BITRATE = "5000k"
    VIDEO_CRF = 23  # 0-51, lower = better quality
    
    # Audio codec settings
    AUDIO_CODEC = "aac"
    AUDIO_BITRATE = "192k"
    AUDIO_SAMPLE_RATE = 44100
    
    # Output formats
    FORMATS = {
        "mp4": {
            "extension": ".mp4",
            "video_codec": "libx264",
            "audio_codec": "aac",
            "container": "mp4",
        },
        "webm": {
            "extension": ".webm",
            "video_codec": "libvpx-vp9",
            "audio_codec": "libopus",
            "container": "webm",
        },
        "gif": {
            "extension": ".gif",
            "video_codec": "gif",
            "audio_codec": None,
            "container": "gif",
        },
    }
    
    # Transition types
    TRANSITIONS = {
        "fade": "fade",
        "fadeblack": "fadeblack",
        "crossfade": "crossfade",
        "dissolve": "dissolve",
        "push": "push",
        "slide": "slide",
        "wipeleft": "wipeleft",
        "wiperight": "wiperight",
    }


class ClipGenerator:
    """Generate video clips from highlights using FFmpeg."""
    
    def __init__(self, output_dir: str = "/tmp/clips"):
        """
        Initialize clip generator.
        
        Args:
            output_dir: Directory for generated clips
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """
        Check if FFmpeg is installed.
        
        Returns:
            True if FFmpeg is available
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✅ FFmpeg is available")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        logger.warning("⚠️ FFmpeg not found. Install with: brew install ffmpeg")
        return False
    
    def extract_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract a clip from a video by timestamp.
        
        Args:
            video_path: Path to source video
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Output file path (optional)
        
        Returns:
            Path to generated clip or None
        """
        try:
            if output_path is None:
                output_path = os.path.join(
                    self.output_dir,
                    f"clip_{int(start_time)}-{int(end_time)}.mp4"
                )
            
            duration = end_time - start_time
            
            # FFmpeg command to extract clip
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c:v", FFmpegConfig.VIDEO_CODEC,
                "-preset", FFmpegConfig.VIDEO_PRESET,
                "-b:v", FFmpegConfig.VIDEO_BITRATE,
                "-crf", str(FFmpegConfig.VIDEO_CRF),
                "-c:a", FFmpegConfig.AUDIO_CODEC,
                "-b:a", FFmpegConfig.AUDIO_BITRATE,
                "-y",  # Overwrite output
                output_path,
            ]
            
            logger.info(f"📹 Extracting clip: {start_time}s → {end_time}s ({duration:.1f}s)")
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"✅ Clip generated: {output_path} ({file_size_mb:.1f} MB)")
                return output_path
            else:
                logger.error(f"❌ FFmpeg error: {result.stderr.decode()}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Clip extraction timeout (>5 min)")
            return None
        except Exception as e:
            logger.error(f"❌ Error extracting clip: {e}")
            return None
    
    def add_fade_effect(
        self,
        video_path: str,
        fade_in: float = 0.5,
        fade_out: float = 0.5,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add fade in/out effects to video.
        
        Args:
            video_path: Path to source video
            fade_in: Fade in duration in seconds
            fade_out: Fade out duration in seconds
            output_path: Output file path (optional)
        
        Returns:
            Path to video with effects or None
        """
        try:
            if output_path is None:
                output_path = os.path.join(
                    self.output_dir,
                    f"clip_faded_{Path(video_path).stem}.mp4"
                )
            
            # Get video duration
            duration_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1:noprint_filename=1",
                video_path,
            ]
            
            result = subprocess.run(duration_cmd, capture_output=True, timeout=10)
            try:
                duration = float(result.stdout.decode().strip())
            except (ValueError, IndexError):
                logger.error("❌ Could not determine video duration")
                return None
            
            # FFmpeg filter for fade effects
            filter_str = f"fade=t=in:st=0:d={fade_in},fade=t=out:st={duration-fade_out}:d={fade_out}"
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", filter_str,
                "-c:v", FFmpegConfig.VIDEO_CODEC,
                "-preset", FFmpegConfig.VIDEO_PRESET,
                "-c:a", "copy",  # Copy audio unchanged
                "-y",
                output_path,
            ]
            
            logger.info(f"✨ Adding fade effects (in: {fade_in}s, out: {fade_out}s)")
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✅ Fade effects applied")
                return output_path
            else:
                logger.error(f"❌ FFmpeg error: {result.stderr.decode()}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Effect processing timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Error adding effects: {e}")
            return None
    
    def add_watermark(
        self,
        video_path: str,
        watermark_text: str = "AI Shorts",
        position: str = "top-right",
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add text watermark to video.
        
        Args:
            video_path: Path to source video
            watermark_text: Text to overlay
            position: Position (top-left, top-right, bottom-left, bottom-right, center)
            output_path: Output file path (optional)
        
        Returns:
            Path to video with watermark or None
        """
        try:
            if output_path is None:
                output_path = os.path.join(
                    self.output_dir,
                    f"clip_watermarked_{Path(video_path).stem}.mp4"
                )
            
            # Position mappings
            positions = {
                "top-left": "x=10:y=10",
                "top-right": "x=w-text_w-10:y=10",
                "bottom-left": "x=10:y=h-text_h-10",
                "bottom-right": "x=w-text_w-10:y=h-text_h-10",
                "center": "x=(w-text_w)/2:y=(h-text_h)/2",
            }
            
            pos = positions.get(position, positions["bottom-right"])
            
            # FFmpeg filter for text overlay
            filter_str = (
                f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white:"
                f"shadowcolor=black:shadowx=2:shadowy=2:{pos}"
            )
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", filter_str,
                "-c:v", FFmpegConfig.VIDEO_CODEC,
                "-preset", FFmpegConfig.VIDEO_PRESET,
                "-c:a", "copy",
                "-y",
                output_path,
            ]
            
            logger.info(f"💧 Adding watermark: '{watermark_text}' ({position})")
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✅ Watermark added")
                return output_path
            else:
                logger.error(f"❌ FFmpeg error: {result.stderr.decode()}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Watermark processing timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Error adding watermark: {e}")
            return None
    
    def convert_format(
        self,
        video_path: str,
        output_format: str = "mp4",
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convert video to different format.
        
        Args:
            video_path: Path to source video
            output_format: Output format (mp4, webm, gif)
            output_path: Output file path (optional)
        
        Returns:
            Path to converted video or None
        """
        try:
            if output_format not in FFmpegConfig.FORMATS:
                logger.error(f"❌ Unsupported format: {output_format}")
                return None
            
            format_config = FFmpegConfig.FORMATS[output_format]
            
            if output_path is None:
                output_path = os.path.join(
                    self.output_dir,
                    f"clip_converted_{Path(video_path).stem}{format_config['extension']}"
                )
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
            ]
            
            # Add video codec settings
            if format_config["video_codec"]:
                cmd.extend(["-c:v", format_config["video_codec"]])
                if format_config["video_codec"] != "gif":
                    cmd.extend(["-preset", FFmpegConfig.VIDEO_PRESET])
                    cmd.extend(["-b:v", FFmpegConfig.VIDEO_BITRATE])
            
            # Add audio codec settings
            if format_config["audio_codec"]:
                cmd.extend(["-c:a", format_config["audio_codec"]])
                cmd.extend(["-b:a", FFmpegConfig.AUDIO_BITRATE])
            else:
                cmd.append("-an")  # No audio
            
            cmd.extend(["-y", output_path])
            
            logger.info(f"🎬 Converting to {output_format.upper()}")
            
            result = subprocess.run(cmd, capture_output=True, timeout=600)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"✅ Converted to {output_format}: {output_path} ({file_size_mb:.1f} MB)")
                return output_path
            else:
                logger.error(f"❌ FFmpeg error: {result.stderr.decode()}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Format conversion timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Error converting format: {e}")
            return None
    
    def _probe_final_mp4(self, path: str) -> bool:
        """Verify the produced file is actually MP4/H.264/yuv420p(+AAC-or-silent).

        Returns False (never raises) on any technical failure, missing/wrong
        streams, or a malformed probe result — the caller treats that as a
        real generation failure, not a valid empty highlight.
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=codec_type,codec_name,pix_fmt",
                    "-of", "json",
                    path,
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(f"❌ ffprobe verification failed: {result.stderr.decode(errors='replace')}")
                return False
            streams = json.loads(result.stdout.decode()).get("streams", [])
        except (OSError, subprocess.TimeoutExpired, ValueError) as e:
            logger.error(f"❌ ffprobe verification error: {e}")
            return False

        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not video or video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
            logger.error(f"❌ Output is not H.264/yuv420p: {video}")
            return False

        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if audio is not None and audio.get("codec_name") != "aac":
            logger.error(f"❌ Output audio is not AAC: {audio}")
            return False

        return True

    def _finalize_clip(self, candidate_path: str, scratch_dir: str, clip_id: str) -> Optional[str]:
        """Verify, guarantee +faststart, and atomically publish one final clip.

        ``candidate_path`` must already be MP4/H.264/AAC (produced upstream);
        this only confirms it and fixes the moov-atom position. Never leaves a
        partial file at the public destination: the remux happens in
        ``scratch_dir`` and only a complete, verified file is renamed in.
        """
        if not self._probe_final_mp4(candidate_path):
            return None

        remuxed_path = os.path.join(scratch_dir, f"{clip_id}.faststart.mp4")
        cmd = [
            "ffmpeg", "-i", candidate_path,
            "-c", "copy",
            "-movflags", "+faststart",
            "-y", remuxed_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            logger.error("❌ +faststart remux timeout")
            return None
        if result.returncode != 0 or not os.path.exists(remuxed_path):
            logger.error(f"❌ +faststart remux failed: {result.stderr.decode(errors='replace')}")
            return None

        final_path = os.path.join(self.output_dir, f"{clip_id}.mp4")
        try:
            os.replace(remuxed_path, final_path)
        except OSError as e:
            logger.error(f"❌ Could not publish final clip: {e}")
            return None
        return final_path

    def generate_from_highlight(
        self,
        video_path: str,
        highlight: Dict[str, Any],
        apply_effects: bool = True,
        output_formats: List[str] = None,
        clip_id: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Generate clip from highlight with all effects and formats.

        All intermediate processing (extraction, fade, watermark) happens in
        an isolated temporary scratch directory, never inside ``output_dir``.
        Only the final, verified MP4 is atomically published — no
        intermediate or unused-format file is ever left behind.

        Args:
            video_path: Path to source video
            highlight: Highlight data with start_time, end_time, score
            apply_effects: Whether to apply fade effects
            output_formats: List of output formats (default: ["mp4"])
            clip_id: stable, collision-free identifier used for the published
                filename (e.g. ``clip_000``); falls back to a timestamp-based
                name if not provided.

        Returns:
            Dict with format -> path mappings
        """
        if output_formats is None:
            output_formats = ["mp4"]

        results: Dict[str, Optional[str]] = {}
        start = highlight.get("start_time", 0)
        end = highlight.get("end_time", 10)
        stem = clip_id or f"clip_{int(start)}-{int(end)}"

        # Scratch space lives *inside* output_dir (not the system temp dir):
        # the final publish step is an atomic os.replace(), which requires
        # the same filesystem — output_dir may be a mounted volume distinct
        # from /tmp in production. The dot-prefix keeps it out of the
        # published-clip namespace: _validate_generated_clips() rejects any
        # "." - prefixed reference, and the retry sweep in worker.py only
        # globs "clip_*", so a scratch dir is never mistaken for a clip.
        scratch_dir = tempfile.mkdtemp(dir=self.output_dir, prefix=f".clipgen-scratch-{stem}-")
        try:
            base_clip = self.extract_clip(
                video_path, start, end,
                output_path=os.path.join(scratch_dir, f"{stem}.base.mp4"),
            )
            if not base_clip:
                logger.error("❌ Failed to extract base clip")
                return results

            if apply_effects:
                processed_clip = self.add_fade_effect(
                    base_clip, fade_in=0.3, fade_out=0.3,
                    output_path=os.path.join(scratch_dir, f"{stem}.faded.mp4"),
                )
                processed_clip = self.add_watermark(
                    processed_clip or base_clip,
                    watermark_text="AI Shorts",
                    output_path=os.path.join(scratch_dir, f"{stem}.watermarked.mp4"),
                )
            else:
                processed_clip = base_clip

            best_candidate = processed_clip or base_clip

            for fmt in output_formats:
                if fmt == "mp4":
                    results[fmt] = self._finalize_clip(best_candidate, scratch_dir, stem)
                elif fmt in FFmpegConfig.FORMATS:
                    converted = self.convert_format(
                        best_candidate, fmt,
                        output_path=os.path.join(scratch_dir, f"{stem}.{fmt}"),
                    )
                    if converted:
                        final_path = os.path.join(self.output_dir, f"{stem}.{fmt}")
                        try:
                            os.replace(converted, final_path)
                            results[fmt] = final_path
                        except OSError as e:
                            logger.error(f"❌ Could not publish {fmt} clip: {e}")
                            results[fmt] = None
                    else:
                        results[fmt] = None
                else:
                    logger.warning(f"⚠️ Unsupported format: {fmt}")

            if results.get("mp4"):
                logger.info(f"✅ Generated clip from highlight ({start}s → {end}s)")
            return results

        except Exception as e:
            logger.error(f"❌ Error generating clip: {e}")
            return results
        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)


def create_clip_generator(output_dir: str = "/tmp/clips") -> ClipGenerator:
    """Factory function to create clip generator."""
    return ClipGenerator(output_dir)
