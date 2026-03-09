"""
clip_selector.py – Score every transcript segment and pick the top N.

Viral score formula (all weights are tunable):
    + numbers/statistics  → high shareability
    + emotional words     → triggers engagement
    + questions           → creates curiosity
    + ideal length        → 15-45 s
    + information density → short words / total words ratio (higher = denser)
    - very long segments  → penalise > 60 s

Returns segments enriched with:
    - viral_score   : float  (0–10)
    - keywords      : list[str]
    - title         : str (first sentence truncated)
"""

import re
import logging
from typing import List, Dict, Any

from backend.config import settings
from backend.ai.viral_scoring   import compute_viral_score
from backend.ai.keyword_extractor import extract_keywords

logger = logging.getLogger(__name__)


def _merge_segments(
    segments: List[Dict[str, Any]],
    min_dur: int,
    max_dur: int,
) -> List[Dict[str, Any]]:
    """
    Merge consecutive short segments into chunks of min_dur..max_dur seconds.

    Faster-Whisper can return very short segments (< 3 s); we merge them
    into coherent clips before scoring.
    """
    if not segments:
        return []

    merged: List[Dict[str, Any]] = []
    current = dict(segments[0])  # shallow copy

    for seg in segments[1:]:
        current_dur = current["end"] - current["start"]
        next_dur    = seg["end"] - seg["start"]

        if current_dur + next_dur <= max_dur:
            # Merge: extend the current chunk
            current["end"]   = seg["end"]
            current["text"] += " " + seg["text"]
            current["words"] = current.get("words", []) + seg.get("words", [])
        else:
            if current_dur >= min_dur:
                merged.append(current)
            current = dict(seg)

    # Don't forget the last chunk
    if current["end"] - current["start"] >= min_dur:
        merged.append(current)

    return merged


def select_top_segments(
    segments: List[Dict[str, Any]],
    max_clips: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Score and rank all segments, return the top N.

    Parameters
    ----------
    segments  : list of dicts from transcription_service
    max_clips : override the default from settings (used for per-user choice)

    Returns
    -------
    Top N segment dicts, each enriched with viral_score, keywords, title.
    """
    min_dur = settings.min_clip_duration
    max_dur = settings.max_clip_duration
    n_clips = max(1, min(max_clips if max_clips is not None else settings.max_clips, 10))

    # ── 1. Merge raw segments into clip-sized chunks ─────────────────────
    chunks = _merge_segments(segments, min_dur, max_dur)
    logger.info(f"Merged into {len(chunks)} scorable chunks.")

    if not chunks:
        logger.warning("No valid chunks produced from transcript.")
        return []

    # ── 2. Score each chunk ───────────────────────────────────────────────
    for chunk in chunks:
        chunk["viral_score"] = compute_viral_score(chunk["text"], chunk["end"] - chunk["start"])
        chunk["keywords"]    = extract_keywords(chunk["text"])
        # Title = first sentence, max 80 chars
        first_sentence = re.split(r"[.!?]", chunk["text"])[0].strip()
        chunk["title"] = first_sentence[:80] if first_sentence else chunk["text"][:80]

    # ── 3. Sort by viral score descending ────────────────────────────────
    chunks.sort(key=lambda c: c["viral_score"], reverse=True)

    top = chunks[:n_clips]
    logger.info(
        f"Selected {len(top)} segments (requested {n_clips}). "
        f"Top score: {top[0]['viral_score']:.2f}" if top else "No segments selected."
    )
    return top
