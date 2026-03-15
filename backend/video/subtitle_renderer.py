"""
subtitle_renderer.py – Render SRT / ASS subtitle files from caption data.

Generates:
  - An SRT file  (simple, widely compatible)
  - An ASS file  (advanced, supports colour/font styling)

These can then be burned into the video by ffmpeg via the `subtitles` filter,
or used as external subtitle tracks.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  SRT helpers
# ──────────────────────────────────────────────


def _srt_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT timestamp format: HH:MM:SS,mmm"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds) // 60 % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def captions_to_srt(
    captions: List[Dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """
    Write an SRT subtitle file from a list of caption dicts.

    Parameters
    ----------
    captions : list of { "text": str, "start": float, "end": float }
    output_path : path for the .srt output file

    Returns
    -------
    Path to the written SRT file.
    """
    path = Path(output_path)
    lines = []
    for idx, cap in enumerate(captions, start=1):
        lines.append(str(idx))
        lines.append(f"{_srt_timestamp(cap['start'])} --> {_srt_timestamp(cap['end'])}")
        lines.append(cap["text"])
        lines.append("")  # blank line separator

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug(f"SRT written: {path}")
    return path


# ──────────────────────────────────────────────
#  ASS helpers  (Advanced SubStation Alpha)
# ──────────────────────────────────────────────

ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,44,&H00FFFF00,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,2,30,30,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ass_timestamp(seconds: float) -> str:
    """Convert float seconds to ASS timestamp format: H:MM:SS.cc"""
    cs = int((seconds % 1) * 100)  # centiseconds
    s = int(seconds) % 60
    m = int(seconds) // 60 % 60
    h = int(seconds) // 3600
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def captions_to_ass(
    captions: List[Dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """
    Write an ASS subtitle file from a list of caption dicts.

    The style is yellow bold text with black outline – optimised for
    short-form vertical video.

    Parameters
    ----------
    captions : list of { "text": str, "start": float, "end": float }
    output_path : path for the .ass output file

    Returns
    -------
    Path to the written ASS file.
    """
    path = Path(output_path)
    lines = [ASS_HEADER]

    for cap in captions:
        # ASS does not support newlines in Dialogue; replace \n with \N
        text = cap["text"].replace("\n", "\\N")
        line = (
            f"Dialogue: 0,"
            f"{_ass_timestamp(cap['start'])},"
            f"{_ass_timestamp(cap['end'])},"
            f"Default,,0,0,0,,{text}"
        )
        lines.append(line)

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug(f"ASS written: {path}")
    return path
