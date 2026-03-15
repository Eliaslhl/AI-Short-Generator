"""
broll_service.py – Match extracted keywords to local B-roll video clips.

The /data/broll/ folder should contain short MP4 clips named after their
subject (e.g. "money.mp4", "technology.mp4", "space.mp4").

The service returns the absolute path to the best matching B-roll clip,
or None if no match is found.
"""

import logging
from pathlib import Path
from typing import List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# Simple keyword → filename stem mapping (extend as needed)
BROLL_KEYWORD_MAP = {
    # Tech
    "technology": ["tech", "computer", "code", "software"],
    "ai": ["ai", "robot", "artificial"],
    # Business
    "money": ["money", "cash", "finance", "invest"],
    "business": ["business", "office", "work"],
    # Science
    "science": ["science", "lab", "research"],
    "space": ["space", "nasa", "planet", "star"],
    # Health
    "health": ["health", "fitness", "exercise", "gym"],
    "food": ["food", "eat", "cooking", "diet"],
    # Nature
    "nature": ["nature", "forest", "mountain", "ocean"],
    "city": ["city", "urban", "street"],
}


def _stem_matches(keyword: str, stems: List[str]) -> bool:
    """Return True if keyword starts with or equals any of the stems."""
    kw = keyword.lower()
    return any(kw.startswith(s) or s.startswith(kw) for s in stems)


def _find_clip_for_keyword(keyword: str, broll_dir: Path) -> Optional[Path]:
    """
    Search for a B-roll clip matching a single keyword.

    Strategy:
    1. Direct file match: <broll_dir>/<keyword>.mp4
    2. Fuzzy match via BROLL_KEYWORD_MAP
    3. Partial filename match
    """
    kw = keyword.lower().strip()

    # ── Direct match ──────────────────────────────────────────────────────
    direct = broll_dir / f"{kw}.mp4"
    if direct.exists():
        return direct

    # ── Map-based match ───────────────────────────────────────────────────
    for topic, synonyms in BROLL_KEYWORD_MAP.items():
        if _stem_matches(kw, synonyms):
            candidate = broll_dir / f"{topic}.mp4"
            if candidate.exists():
                return candidate

    # ── Partial filename scan ─────────────────────────────────────────────
    for mp4 in broll_dir.glob("*.mp4"):
        if kw in mp4.stem.lower():
            return mp4

    return None


def find_broll(keywords: List[str]) -> Optional[str]:
    """
    Find the best B-roll clip for a list of keywords.

    Parameters
    ----------
    keywords : list[str]
        Keywords extracted from the segment (from keyword_extractor).

    Returns
    -------
    Absolute path string to the matching MP4, or None.
    """
    broll_dir = Path(settings.broll_dir)

    if not broll_dir.exists():
        logger.warning(f"B-roll directory not found: {broll_dir}")
        return None

    for keyword in keywords:
        match = _find_clip_for_keyword(keyword, broll_dir)
        if match:
            logger.debug(f"B-roll match: '{keyword}' → {match}")
            return str(match)

    logger.debug("No B-roll match found for keywords: %s", keywords)
    return None
