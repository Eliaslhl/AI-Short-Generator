"""
video_editor.py – Render a vertical 9:16 short clip using MoviePy + ffmpeg.

Pipeline for each clip:
  1. Cut the segment from the source video
  2. Crop / pad to 1080×1920 (9:16 portrait)
  3. Overlay the hook text at the top
  4. Overlay styled emoji captions at the bottom
  5. Optionally overlay a B-roll clip (picture-in-picture)
  6. Export as MP4

Returns a dict with clip metadata (used by the API response).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from backend.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Font resolution  (PIL needs a path or a known alias)
# ──────────────────────────────────────────────
def _resolve_font(prefer_bold: bool = True) -> str:
    """
    Return a usable font path for PIL/MoviePy TextClip.
    Tries common macOS / Linux / Windows paths in order.
    Falls back to the first working one.
    """
    import os
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",   # macOS
            "/System/Library/Fonts/Supplemental/Impact.ttf",       # macOS
            "/System/Library/Fonts/Arial.ttf",                     # macOS (older)
            "/Library/Fonts/Arial Bold.ttf",                       # macOS user fonts
        ]
        if prefer_bold else
        [
            "/System/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    ) + [
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        # Windows
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/impact.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Last resort: let PIL pick whatever "Arial" resolves to
    return "Arial"


FONT_BOLD   = _resolve_font(prefer_bold=True)
FONT_NORMAL = _resolve_font(prefer_bold=False)
logger.info(f"Using fonts — bold: {FONT_BOLD} | normal: {FONT_NORMAL}")

# ──────────────────────────────────────────────
#  Colour / size constants
# ──────────────────────────────────────────────
HOOK_FONT_SIZE    = 52
CAPTION_FONT_SIZE = 44
HOOK_COLOR        = "white"
CAPTION_COLOR     = "#FFFF00"      # yellow for captions
STROKE_COLOR      = "black"
STROKE_WIDTH      = 3

# ──────────────────────────────────────────────
#  Subtitle style presets  (Pro feature)
# ──────────────────────────────────────────────
# Note: font keys are replaced at runtime with FONT_BOLD / FONT_NORMAL
# after the _resolve_font() call below.
SUBTITLE_STYLES: dict[str, dict] = {
    "default":  {"color": "#FFFF00", "font": None, "stroke_color": "black",   "stroke_width": 3},
    "bold":     {"color": "white",   "font": None, "stroke_color": "black",   "stroke_width": 4},
    "outlined": {"color": "white",   "font": None, "stroke_color": "#3B82F6", "stroke_width": 4},
    "neon":     {"color": "#00FF88", "font": None, "stroke_color": "black",   "stroke_width": 5},
    "minimal":  {"color": "white",   "font": None, "stroke_color": None,      "stroke_width": 0},
}


def _make_output_path(job_id: str, clip_index: int) -> Path:
    out_dir = Path(settings.clips_dir) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"clip_{clip_index + 1:02d}.mp4"


def _crop_to_portrait(clip):
    """
    Crop a landscape clip to 9:16 portrait format.

    Strategy: centre-crop horizontally, keep full height, then resize.
    Falls back to adding black bars if the clip is already taller.
    """
    from moviepy.video.fx import Crop, Resize

    target_w = settings.output_width    # 1080
    target_h = settings.output_height   # 1920
    target_ratio = target_w / target_h  # 0.5625

    w, h = clip.size
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Landscape → crop the sides
        new_w = int(h * target_ratio)
        x_center = w / 2
        clip = Crop(x_center=x_center, width=new_w).apply(clip)
    elif current_ratio < target_ratio:
        # Portrait but different ratio → add side bars (pillarbox)
        new_h = int(w / target_ratio)
        y_center = h / 2
        clip = Crop(y_center=y_center, height=new_h).apply(clip)

    # Resize to exact output dimensions
    clip = Resize((target_w, target_h)).apply(clip)
    return clip


def _add_hook_overlay(clip, hook_text: str):
    """Add the hook text at the top of the clip."""
    try:
        from moviepy import TextClip, CompositeVideoClip

        # Wrap long hooks
        words = hook_text.split()
        lines = []
        for i in range(0, len(words), 4):
            lines.append(" ".join(words[i:i + 4]))
        wrapped = "\n".join(lines)

        txt = (
            TextClip(
                text=wrapped,
                font_size=HOOK_FONT_SIZE,
                font=FONT_BOLD,
                color=HOOK_COLOR,
                stroke_color=STROKE_COLOR,
                stroke_width=STROKE_WIDTH,
                method="caption",
                size=(settings.output_width - 80, None),
                text_align="center",
            )
            .with_duration(min(clip.duration, 4.0))
            .with_position(("center", 80))
        )
        return CompositeVideoClip([clip, txt])
    except Exception as exc:
        logger.warning(f"Could not add hook overlay: {exc}")
        return clip


def _add_caption_overlays(clip, captions: List[Dict[str, Any]], seg_start: float, subtitle_style: str = "default"):
    """Overlay timed caption lines at the bottom of the clip."""
    try:
        from moviepy import TextClip, CompositeVideoClip

        style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["default"])
        cap_color    = style["color"]
        # Use minimal style → normal font, all others → bold
        cap_font     = FONT_NORMAL if subtitle_style == "minimal" else FONT_BOLD
        cap_stroke_c = style["stroke_color"] or "black"
        cap_stroke_w = style["stroke_width"]

        overlay_clips = [clip]
        bottom_y = settings.output_height - 220   # 220 px from bottom

        for cap in captions:
            # Caption times are relative to segment start
            cap_start = cap["start"] - seg_start
            cap_end   = cap["end"]   - seg_start

            # Clamp to clip duration
            cap_start = max(0.0, min(cap_start, clip.duration - 0.1))
            cap_end   = max(cap_start + 0.1, min(cap_end, clip.duration))
            duration  = cap_end - cap_start

            if duration <= 0:
                continue

            txt = (
                TextClip(
                    text=cap["text"],
                    font_size=CAPTION_FONT_SIZE,
                    font=cap_font,
                    color=cap_color,
                    stroke_color=cap_stroke_c,
                    stroke_width=cap_stroke_w,
                    method="caption",
                    size=(settings.output_width - 100, None),
                    text_align="center",
                )
                .with_start(cap_start)
                .with_duration(duration)
                .with_position(("center", bottom_y))
            )
            overlay_clips.append(txt)

        return CompositeVideoClip(overlay_clips)
    except Exception as exc:
        logger.error(f"Caption overlay error (style={subtitle_style}): {exc}", exc_info=True)
        return clip


def _add_broll_overlay(main_clip, broll_path: str):
    """
    Add a B-roll clip as a picture-in-picture in the top-right corner.
    The B-roll is looped / trimmed to match the main clip duration.
    """
    try:
        from moviepy import VideoFileClip, CompositeVideoClip, concatenate_videoclips
        from moviepy.video.fx import Resize

        broll = VideoFileClip(broll_path).without_audio()

        # Loop if shorter, trim if longer
        if broll.duration < main_clip.duration:
            repeats = int(main_clip.duration / broll.duration) + 1
            broll = concatenate_videoclips([broll] * repeats)
        broll = broll.subclipped(0, main_clip.duration)

        # Resize B-roll to ¼ of screen width
        pip_w = settings.output_width // 4
        broll = Resize(width=pip_w).apply(broll)

        # Position: top-right corner with padding
        padding = 20
        broll = broll.with_position((settings.output_width - pip_w - padding, padding))  # type: ignore[union-attr]

        return CompositeVideoClip([main_clip, broll])
    except Exception as exc:
        logger.warning(f"Could not add B-roll overlay: {exc}")
        return main_clip


def render_clip(
    video_path: str,
    segment: Dict[str, Any],
    job_id: str,
    clip_index: int,
    subtitle_style: str = "default",
) -> Dict[str, Any]:
    """
    Render a single short clip from a source video segment.

    Parameters
    ----------
    video_path : str
        Path to the full downloaded video.
    segment : dict
        Segment dict from clip_selector (includes start/end/text/hook/captions/broll).
    job_id : str
        Unique job ID for namespacing output files.
    clip_index : int
        Zero-based index of this clip (used for output filename).

    Returns
    -------
    dict with file URL, title, duration, viral_score, hook.
    """
    from moviepy import VideoFileClip

    start    = segment["start"]
    end      = segment["end"]
    duration = end - start
    hook     = segment.get("hook", "")
    captions = segment.get("captions", [])
    broll    = segment.get("broll")
    # "ai_title" = Pro+ generated title; "title" = clip_selector first-sentence fallback
    ai_title   = segment.get("ai_title") or segment.get("title", f"Clip {clip_index + 1}")
    hashtags   = segment.get("hashtags")   # Pro+ only

    output_path = _make_output_path(job_id, clip_index)

    logger.info(f"Rendering clip {clip_index + 1}: {start:.1f}s – {end:.1f}s  →  {output_path.name}")

    try:
        # ── Load and cut source video ─────────────────────────────────────
        source = VideoFileClip(video_path)
        clip   = source.subclipped(start, min(end, source.duration))

        # ── Convert to portrait 9:16 ──────────────────────────────────────
        clip = _crop_to_portrait(clip)

        # ── Overlays ──────────────────────────────────────────────────────
        if hook:
            clip = _add_hook_overlay(clip, hook)

        if captions:
            clip = _add_caption_overlays(clip, captions, start, subtitle_style)

        if broll:
            clip = _add_broll_overlay(clip, broll)

        # ── Export ────────────────────────────────────────────────────────
        clip.write_videofile(  # type: ignore[union-attr]
            str(output_path),
            fps=settings.output_fps,
            codec="libx264",
            audio_codec="aac",
            bitrate=settings.output_bitrate,
            threads=4,
            logger=None,     # suppress MoviePy's verbose progress bar
        )

        source.close()
        clip.close()

        logger.info(f"Clip {clip_index + 1} saved: {output_path}")

    except Exception as exc:
        logger.error(f"Error rendering clip {clip_index + 1}: {exc}")
        # Create a minimal placeholder so the pipeline doesn't crash entirely
        _create_placeholder_clip(output_path, segment)

    # ── Return metadata ───────────────────────────────────────────────────
    relative_url = f"/clips/{job_id}/{output_path.name}"
    return {
        "file":        relative_url,
        "title":       ai_title,
        "duration":    round(duration, 1),
        "viral_score": round(segment.get("viral_score", 0.0), 2),
        "hook":        hook,
        "hashtags":    hashtags,
        "start":       round(start, 2),
        "end":         round(end, 2),
    }


def _create_placeholder_clip(output_path: Path, segment: Dict[str, Any]):
    """
    Create a minimal black MP4 as a fallback when rendering fails.
    Uses ffmpeg directly to avoid MoviePy overhead.
    """
    import subprocess
    duration = segment["end"] - segment["start"]
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=black:s=1080x1920:d={duration:.2f}",
        "-c:v", "libx264", "-t", str(duration),
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True)
    logger.warning(f"Placeholder clip created: {output_path}")
