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
import os

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
    # Keep the hook text in metadata but do NOT render it on the video
    # (user requested no title at the top). Use `hook_text` for metadata and
    # leave `overlay_hook` empty so no top overlay is produced.
    hook_text = segment.get("hook", "")
    overlay_hook = None
    captions = segment.get("captions", [])
    broll    = segment.get("broll")
    # "ai_title" = Pro+ generated title; "title" = clip_selector first-sentence fallback
    ai_title   = segment.get("ai_title") or segment.get("title", f"Clip {clip_index + 1}")
    hashtags   = segment.get("hashtags")   # Pro+ only

    output_path = _make_output_path(job_id, clip_index)

    logger.info(f"Rendering clip {clip_index + 1}: {start:.1f}s – {end:.1f}s  →  {output_path.name}")

    # First try an ffmpeg-based fast path (hardware encoder if available).
    try:
        # pass overlay_hook (None) to avoid burning a title/hook at the top
        ffmpeg_success = _render_with_ffmpeg(
            video_path, start, end, output_path, overlay_hook, captions, subtitle_style, broll
        )
        if ffmpeg_success:
            logger.info(f"Clip {clip_index + 1} saved (ffmpeg): {output_path}")
            relative_url = f"/clips/{job_id}/{output_path.name}"
            return {
                "file": relative_url,
                "title": ai_title,
                "duration": round(duration, 1),
                "viral_score": round(segment.get("viral_score", 0.0), 2),
                "hook": hook_text,
                "hashtags": hashtags,
                "start": round(start, 2),
                "end": round(end, 2),
            }
    except Exception as exc:
        logger.warning(f"ffmpeg fast-path failed, falling back to MoviePy: {exc}")

    try:
        # ── Load and cut source video ─────────────────────────────────────
        source = VideoFileClip(video_path)
        clip   = source.subclipped(start, min(end, source.duration))

        # ── Convert to portrait 9:16 ──────────────────────────────────────
        clip = _crop_to_portrait(clip)

        # ── Overlays ──────────────────────────────────────────────────────
        # Do not add the hook overlay (title at top) — keep only bottom captions

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
    # Attempt to create a thumbnail (poster) image next to the video file.
    poster_rel = None
    try:
        # prefer WebP thumbnails for better quality-to-size ratio
        thumb_path = output_path.with_suffix('.webp')
        _create_thumbnail(str(output_path), float(duration), str(thumb_path))
        poster_rel = f"/clips/{job_id}/{thumb_path.name}"
    except Exception as exc:
        logger.warning(f"Could not create thumbnail for {output_path}: {exc}")

    return {
        "file":        relative_url,
        "poster":      poster_rel,
        "title":       ai_title,
        "duration":    round(duration, 1),
        "viral_score": round(segment.get("viral_score", 0.0), 2),
        "hook":        hook_text,
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


def _create_thumbnail(video_path: str, at_time: float, out_path: str) -> bool:
    """
    Create a single-frame JPEG thumbnail for the given video file.

    Params
    ------
    video_path: path to the rendered clip
    at_time: desired thumbnail time (seconds) — typically the clip duration
    out_path: output path for the thumbnail image
    """
    import subprocess
    try:
        # pick a timestamp roughly in the middle, but keep a small margin
        mid = max(0.1, min(at_time / 2.0, max(0.1, at_time - 0.1)))
        # Use libwebp encoder via ffmpeg for a compact, high-quality thumbnail.
        # Resize width to 360px and preserve aspect ratio.
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{mid:.3f}",
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-vf",
            "scale=360:-1:flags=lanczos",
            # use libwebp if available; ffmpeg will choose encoder by extension otherwise
            "-compression_level",
            "6",
            "-q:v",
            "60",
            str(out_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"Thumbnail created: {out_path}")
        return True
    except Exception as exc:
        logger.warning(f"Failed to create thumbnail for {video_path}: {exc}")
        return False


def _render_with_ffmpeg(
    video_path: str,
    start: float,
    end: float,
    output_path: Path,
    hook: str | None,
    captions: List[Dict[str, Any]] | None,
    subtitle_style: str,
    broll: str | None,
) -> bool:
    """
    Fast path renderer using ffmpeg. Returns True on success.

    Strategy:
    - Extract the requested segment via -ss/-t
    - Scale/pad to 1080x1920 using ffmpeg filters
    - Burn subtitles from a temporary SRT if captions provided
    - Overlay a hook PNG (generated via Pillow) if hook provided
    - Use hardware encoder configured in settings.ffmpeg_hwaccel when available
    """
    import shlex
    from subprocess import run, CalledProcessError
    import tempfile

    duration = max(0.1, end - start)

    # Ensure parent exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_files = []
    try:
        # 1) Optionally create hook image
        hook_png = None
        if hook:
            fd, hook_png = tempfile.mkstemp(suffix=".png", prefix="hook_")
            os.close(fd)
            _render_hook_image(hook, hook_png)
            tmp_files.append(hook_png)

        # 2) Optionally create subtitles SRT (relative times)
        srt_path = None
        if captions:
            fd, srt_path = tempfile.mkstemp(suffix=".srt", prefix="caps_")
            os.close(fd)
            _write_srt(captions, start, srt_path)
            tmp_files.append(srt_path)

        # 3) Build filter graph: scale/pad to 1080x1920 and overlay hook if present
        vf_parts = []
        # scale/pad to ensure 1080x1920 output while preserving aspect
        vf_parts.append("scale=1080:1920:force_original_aspect_ratio=decrease")
        vf_parts.append("pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")
        vf_main = ",".join(vf_parts)

        filter_complex = None
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-t", f"{duration:.3f}", "-i", str(video_path)]

        # If hook image present, add as second input and use complex filter to overlay
        if hook_png:
            cmd += ["-i", hook_png]
            # overlay near top center (x=(W-w)/2, y=80)
            filter_complex = f"[0:v]{vf_main}[v0];[v0][1:v]overlay=(W-w)/2:80"

        # Subtitles: use subtitles filter if srt exists (applied after scaling/pad)
        if srt_path:
            if filter_complex:
                filter_complex = filter_complex + f",subtitles='{srt_path}'"
            else:
                filter_complex = vf_main + f",subtitles='{srt_path}'"

        if filter_complex:
            # If we used overlay, ffmpeg produced [v0] as intermediate, but final filter may be in [v0]
            # We'll map the first video stream output automatically by not specifying -map for video.
            cmd += ["-filter_complex", filter_complex]
        else:
            # simple scale/pad via -vf
            cmd += ["-vf", vf_main]

        # Map audio if present
        cmd += ["-map", "0:a?", "-c:a", "aac"]

        # Choose encoder
        hw = settings.ffmpeg_hwaccel or ""
        if hw.lower() == "videotoolbox":
            cmd += ["-c:v", "h264_videotoolbox", "-b:v", settings.output_bitrate]
        elif hw.lower() == "nvenc":
            cmd += ["-c:v", "h264_nvenc", "-b:v", settings.output_bitrate]
        else:
            # software fallback
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-b:v", settings.output_bitrate]

        cmd += [str(output_path)]

        logger.debug(f"Running ffmpeg command: {' '.join(shlex.quote(p) for p in cmd)}")
        run(cmd, capture_output=True, text=True, check=True)
        return True

    except CalledProcessError as e:
        logger.error(f"ffmpeg failed: {e.stderr}\n{e.stdout}")
        return False
    finally:
        # Clean up tmp files
        for p in tmp_files:
            try:
                os.unlink(p)
            except Exception:
                pass


def _render_hook_image(hook_text: str, out_path: str):
    """Render hook text to a transparent PNG using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Simple wrapping: max width in chars
        max_chars = 28
        words = hook_text.split()
        lines = []
        cur = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + (1 if cur else 0) > max_chars:
                lines.append(" ".join(cur))
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += len(w) + (1 if cur else 0)
        if cur:
            lines.append(" ".join(cur))

        font_path = FONT_BOLD if FONT_BOLD else "Arial"
        font_size = HOOK_FONT_SIZE
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

        # Estimate image size (use font size heuristics to avoid PIL API differences)
        line_h = font_size + 8
        img_h = line_h * len(lines) + 20
        img_w = settings.output_width - 160

        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        y = 10
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
            except Exception:
                # Fallback estimate
                w = int(len(line) * font_size * 0.6)

            x = int((img_w - w) / 2)
            try:
                draw.text((x, y), line, font=font, fill=HOOK_COLOR, stroke_width=STROKE_WIDTH, stroke_fill=STROKE_COLOR)
            except TypeError:
                draw.text((x, y), line, font=font, fill=HOOK_COLOR)
            y += line_h

        img.save(out_path)
    except Exception as exc:
        logger.warning(f"Could not render hook image: {exc}")


def _write_srt(captions: List[Dict[str, Any]], seg_start: float, out_srt: str):
    """Write a simple SRT file with captions times relative to segment start."""
    def _fmt(t: float) -> str:
        # t in seconds -> hh:mm:ss,ms
        ms = int((t - int(t)) * 1000)
        s = int(t) % 60
        m = (int(t) // 60) % 60
        h = int(t) // 3600
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(out_srt, "w", encoding="utf-8") as fh:
        for i, cap in enumerate(captions, start=1):
            start_r = max(0.0, cap["start"] - seg_start)
            end_r = max(0.0, cap["end"] - seg_start)
            fh.write(f"{i}\n")
            fh.write(f"{_fmt(start_r)} --> {_fmt(end_r)}\n")
            # escape newlines
            txt = cap.get("text", "").replace("\n", " ").strip()
            fh.write(txt + "\n\n")


def _write_ass(captions: List[Dict[str, Any]], seg_start: float, out_ass: str):
    """Write a minimal ASS file with a default style and the given captions.

    ASS timestamps use centiseconds. We'll write a small header and the
    Dialogue lines. This avoids an extra dependency but is good enough
    for styled subtitle burning via libass.
    """
    def _fmt_ass(t: float) -> str:
        # ASS uses H:MM:SS.cc (centiseconds)
        total_cs = int(round(t * 100))
        cs = total_cs % 100
        total_s = total_cs // 100
        s = total_s % 60
        m = (total_s // 60) % 60
        h = total_s // 3600
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    header = """[Script Info]
; Script generated by AI-Shorts-Generator
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,44,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(out_ass, "w", encoding="utf-8") as fh:
        fh.write(header)
        for cap in captions:
            start_r = max(0.0, cap.get("start", 0.0) - seg_start)
            end_r = max(0.0, cap.get("end", 0.0) - seg_start)
            text = cap.get("text", "").replace("\n", " ").strip()
            line = f"Dialogue: 0,{_fmt_ass(start_r)},{_fmt_ass(end_r)},Default,,0,0,0,,{text}\n"
            fh.write(line)
