"""
transcription_service.py – Transcribe a video file with Faster-Whisper.

Returns a list of segment dicts:
    {
        "start":    float,   # seconds
        "end":      float,   # seconds
        "text":     str,     # transcribed text
        "words":    list,    # word-level timestamps (if available)
    }
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from faster_whisper import WhisperModel

from backend.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Lazy-loaded model singleton (avoids reloading on every call)
# ──────────────────────────────────────────────
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(
            f"Loading Faster-Whisper model '{settings.whisper_model}' "
            f"on device '{settings.whisper_device}'…"
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type="int8",         # fast & memory-efficient
        )
        logger.info("Whisper model loaded.")
    return _model


def transcribe_video(video_path: str, language: str | None = None) -> List[Dict[str, Any]]:
    """
    Transcribe the audio track of a video file.

    Parameters
    ----------
    video_path : str
        Absolute path to the MP4 (or any ffmpeg-readable file).
    language : str | None
        ISO-639-1 language code (e.g. "fr", "en", "es").
        None or "" → Whisper auto-detects the language.

    Returns
    -------
    List of segment dicts with start/end timestamps and text.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    model = _get_model()

    # Explicit language overrides the .env default; None = auto-detect
    lang = language if language else (settings.whisper_language or None)

    logger.info(f"Transcribing {path.name} (language={lang or 'auto'})…")
    segments_iter, info = model.transcribe(
        str(path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,         # skip silent sections
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    segments: List[Dict[str, Any]] = []
    for seg in segments_iter:
        words = []
        if seg.words:
            words = [
                {"word": w.word, "start": w.start, "end": w.end, "prob": w.probability}
                for w in seg.words
            ]
        segments.append(
            {
                "start": seg.start,
                "end":   seg.end,
                "text":  seg.text.strip(),
                "words": words,
            }
        )

    logger.info(f"Transcription complete: {len(segments)} segments detected.")
    return segments
