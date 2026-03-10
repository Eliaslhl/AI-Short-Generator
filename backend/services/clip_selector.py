"""
clip_selector.py – Score every transcript segment and pick the top N.

Viral score formula (all weights are tunable):
    + numbers/statistics  → high shareability
    + emotional words     → triggers engagement
    + questions           → creates curiosity
    + ideal length        → 15-45 s
    + information density → short words / total words ratio (higher = denser)
    - very long segments  → penalise > 60 s

Precision improvements:
    - Cuts are snapped to sentence boundaries (. ! ?) using word timestamps
    - 0.3 s audio padding added before/after each clip
    - Overlapping clips are deduplicated

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

# How much silence/audio to keep before and after the spoken content
CLIP_PADDING_SECS = 0.3


def _find_sentence_boundary(words: List[Dict], target_end: float, search_window: float = 3.0) -> float:
    """
    Given a list of word-level timestamps, find the end time of the last word
    that ends a sentence (followed by . ! ?) within `search_window` seconds
    before `target_end`.

    Falls back to `target_end` if no sentence boundary is found.
    """
    if not words:
        return target_end

    # Look for words ending a sentence within the search window
    candidates = [
        w for w in words
        if w["end"] <= target_end and w["end"] >= target_end - search_window
        and re.search(r"[.!?]$", w["word"].strip())
    ]

    if candidates:
        # Pick the one closest to target_end
        best = max(candidates, key=lambda w: w["end"])
        logger.debug(f"Snapped clip end from {target_end:.2f}s → {best['end']:.2f}s (sentence boundary)")
        return best["end"]

    return target_end


def _find_sentence_start(words: List[Dict], target_start: float, search_window: float = 2.0) -> float:
    """
    Find the start of the first complete sentence at or after `target_start`.
    Looks for a word that starts a new sentence (preceded by . ! ? or is the first word).

    Falls back to `target_start` if no better start is found.
    """
    if not words:
        return target_start

    # Find all words in the window after target_start
    window_words = [w for w in words if w["start"] >= target_start and w["start"] <= target_start + search_window]

    if not window_words:
        return target_start

    # Find the first word that starts a new sentence
    # (preceded by a word ending in punctuation, or is simply the first one)
    for i, w in enumerate(window_words):
        if i == 0:
            # Check if the word before target_start ended a sentence
            prev_words = [pw for pw in words if pw["end"] <= target_start]
            if prev_words:
                last_prev = max(prev_words, key=lambda pw: pw["end"])
                if re.search(r"[.!?]$", last_prev["word"].strip()):
                    return w["start"]
            # No previous words or no sentence end → use as-is
            return target_start
        # Check if the previous window word ended a sentence
        prev = window_words[i - 1]
        if re.search(r"[.!?]$", prev["word"].strip()):
            return w["start"]

    return target_start


def _merge_segments(
    segments: List[Dict[str, Any]],
    min_dur: int,
    max_dur: int,
) -> List[Dict[str, Any]]:
    """
    Merge consecutive short segments into chunks of min_dur..max_dur seconds.
    Cuts are snapped to sentence boundaries using word-level timestamps.
    """
    if not segments:
        return []

    merged: List[Dict[str, Any]] = []
    current = dict(segments[0])
    current["words"] = list(current.get("words", []))

    for seg in segments[1:]:
        current_dur = current["end"] - current["start"]
        next_dur    = seg["end"] - seg["start"]

        if current_dur + next_dur <= max_dur:
            # Merge: extend the current chunk
            current["end"]   = seg["end"]
            current["text"] += " " + seg["text"]
            current["words"] = current["words"] + seg.get("words", [])
        else:
            if current_dur >= min_dur:
                # ── Snap end to sentence boundary ────────────────────────
                snapped_end = _find_sentence_boundary(
                    current["words"], current["end"], search_window=3.0
                )
                current["end"] = snapped_end
                merged.append(current)
            current = dict(seg)
            current["words"] = list(seg.get("words", []))

    # Last chunk
    if current["end"] - current["start"] >= min_dur:
        snapped_end = _find_sentence_boundary(
            current["words"], current["end"], search_window=3.0
        )
        current["end"] = snapped_end
        merged.append(current)

    return merged


def _add_padding(
    segment: Dict[str, Any],
    video_duration: float,
    padding: float = CLIP_PADDING_SECS,
) -> Dict[str, Any]:
    """Extend start/end by `padding` seconds, clamped to video bounds."""
    seg = dict(segment)
    seg["start"] = max(0.0, seg["start"] - padding)
    seg["end"]   = min(video_duration, seg["end"] + padding)
    return seg


def _deduplicate(segments: List[Dict[str, Any]], overlap_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Remove clips that overlap significantly with a higher-scoring clip.
    `overlap_threshold` = fraction of a clip's duration that must overlap to be removed.
    """
    kept: List[Dict[str, Any]] = []
    for seg in segments:
        overlapping = False
        for k in kept:
            # Compute overlap duration
            overlap = min(seg["end"], k["end"]) - max(seg["start"], k["start"])
            seg_dur = seg["end"] - seg["start"]
            if overlap > 0 and seg_dur > 0 and (overlap / seg_dur) >= overlap_threshold:
                overlapping = True
                break
        if not overlapping:
            kept.append(seg)
    return kept


def select_top_segments(
    segments: List[Dict[str, Any]],
    max_clips: int | None = None,
    video_duration: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Score and rank all segments, return the top N.

    Parameters
    ----------
    segments       : list of dicts from transcription_service
    max_clips      : override the default from settings
    video_duration : total video duration in seconds (for padding clamping)

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
        first_sentence = re.split(r"[.!?]", chunk["text"])[0].strip()
        chunk["title"] = first_sentence[:80] if first_sentence else chunk["text"][:80]

    # ── 3. Sort by viral score descending ────────────────────────────────
    chunks.sort(key=lambda c: c["viral_score"], reverse=True)

    # ── 4. Deduplicate overlapping clips ─────────────────────────────────
    chunks = _deduplicate(chunks)

    # ── 5. Take top N and add padding ────────────────────────────────────
    top = chunks[:n_clips]
    if video_duration > 0:
        top = [_add_padding(seg, video_duration) for seg in top]

    logger.info(
        f"Selected {len(top)} segments (requested {n_clips}). "
        + (f"Top score: {top[0]['viral_score']:.2f}" if top else "No segments selected.")
    )
    return top
