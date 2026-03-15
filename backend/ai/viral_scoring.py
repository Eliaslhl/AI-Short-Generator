"""
viral_scoring.py – Compute a viral potential score for a text segment.

Score components (each 0–10, weighted sum normalised to 0–10):

  1. emotion_score      – emotional trigger word density
  2. numbers_score      – statistics / figures increase credibility
  3. question_score     – questions create curiosity / retention
  4. storytelling_score – narrative markers (story arc indicators)
  5. urgency_score      – time pressure / scarcity language
  6. contrast_score     – opposition / surprise language
  7. length_score       – sweet spot: 60-150 words (≈ 30-60 s speech)
  8. density_score      – short words ratio (punchy, direct language)
  9. duration_score     – clip duration ideal 30-60 s
 10. momentum_score     – strong opening hook (first 30 words)

Weights are defined in WEIGHTS and sum to 1.0.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Word lists
# ──────────────────────────────────────────────

EMOTION_WORDS = {
    # Positive high-energy
    "amazing",
    "incredible",
    "unbelievable",
    "revolutionary",
    "breakthrough",
    "secret",
    "hidden",
    "revealed",
    "shocking",
    "insane",
    "mind-blowing",
    "powerful",
    "ultimate",
    "best",
    "perfect",
    "genius",
    "brilliant",
    "extraordinary",
    "phenomenal",
    "magnificent",
    "explosive",
    "stunning",
    "game-changer",
    "legendary",
    "iconic",
    "epic",
    "wild",
    "crazy",
    "awesome",
    "outstanding",
    "exceptional",
    "remarkable",
    "terrific",
    # Negative / dramatic
    "dangerous",
    "deadly",
    "terrifying",
    "scary",
    "forbidden",
    "illegal",
    "banned",
    "censored",
    "controversial",
    "dark",
    "tragic",
    "disaster",
    "crisis",
    "worst",
    "failed",
    "wrong",
    "mistake",
    "warning",
    "risk",
    "threat",
    "collapse",
    "destroy",
    "horrifying",
    "nightmare",
    "catastrophe",
    "devastating",
    "fatal",
    # Curiosity / mystery
    "truth",
    "lie",
    "myth",
    "fact",
    "real",
    "fake",
    "never",
    "always",
    "everyone",
    "nobody",
    "unknown",
    "mystery",
    "bizarre",
    "strange",
    "weird",
    "odd",
    "secret",
    "hidden",
    # Social proof & scale
    "million",
    "billion",
    "viral",
    "trending",
    "popular",
    "famous",
    "record",
    "first",
    "last",
    "only",
    "unique",
    "exclusive",
    "world",
    "global",
    "history",
    "ever",
    "greatest",
}

STORYTELLING_MARKERS = {
    "i was",
    "it started",
    "one day",
    "back then",
    "years ago",
    "suddenly",
    "everything changed",
    "i realized",
    "i discovered",
    "i never thought",
    "nobody told me",
    "what happened next",
    "the moment i",
    "that's when",
    "here's what",
    "the truth is",
    "turns out",
    "what i found",
    "the real reason",
    "nobody knows",
    "most people",
    "they don't want",
    "let me tell you",
    "you won't believe",
    "this is the story",
    "it all began",
    "from that day",
    "i have to share",
}

URGENCY_WORDS = {
    "now",
    "today",
    "immediately",
    "urgent",
    "critical",
    "deadline",
    "limited",
    "last chance",
    "before it's too late",
    "running out",
    "disappearing",
    "expiring",
    "final",
    "hurry",
    "quickly",
    "right now",
    "this week",
    "don't wait",
}

CONTRAST_WORDS = {
    "but",
    "however",
    "although",
    "despite",
    "instead",
    "actually",
    "surprisingly",
    "unexpectedly",
    "ironically",
    "contrary",
    "wrong",
    "turns out",
    "in reality",
    "in fact",
    "thought it was",
    "nobody expected",
    "against all odds",
    "what people miss",
    "the opposite",
    "plot twist",
}

# Component weights — must sum to 1.0
WEIGHTS = {
    "emotion": 0.22,
    "numbers": 0.10,
    "question": 0.10,
    "storytelling": 0.12,
    "urgency": 0.08,
    "contrast": 0.08,
    "length": 0.10,
    "density": 0.08,
    "duration": 0.08,
    "momentum": 0.04,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"

# ──────────────────────────────────────────────
#  Individual scoring functions  (each returns 0–10)
# ──────────────────────────────────────────────


def _emotion_score(text: str) -> float:
    """Emotional trigger word density — capped at 5 hits → 10.0."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in EMOTION_WORDS)
    return min(hits / 5 * 10.0, 10.0)


def _numbers_score(text: str) -> float:
    """Presence of numbers, percentages, and statistics."""
    matches = re.findall(r"\b\d[\d,\.]*\s*[%xX]?\b", text)
    # 0 numbers = 0, 1 = 5, 2 = 8, 3+ = 10
    n = len(matches)
    if n == 0:
        return 0.0
    if n == 1:
        return 5.0
    if n == 2:
        return 8.0
    return 10.0


def _question_score(text: str) -> float:
    """Questions create curiosity — 2+ questions = max score."""
    count = text.count("?")
    return min(count / 2 * 10.0, 10.0)


def _storytelling_score(text: str) -> float:
    """Detect narrative/story arc markers — viewers stay for stories."""
    lower = text.lower()
    hits = sum(1 for marker in STORYTELLING_MARKERS if marker in lower)
    return min(hits / 3 * 10.0, 10.0)


def _urgency_score(text: str) -> float:
    """Time pressure / scarcity language — drives action."""
    lower = text.lower()
    hits = sum(1 for w in URGENCY_WORDS if w in lower)
    return min(hits / 3 * 10.0, 10.0)


def _contrast_score(text: str) -> float:
    """Surprise / opposition language — creates engagement through tension."""
    lower = text.lower()
    hits = sum(1 for w in CONTRAST_WORDS if w in lower)
    return min(hits / 4 * 10.0, 10.0)


def _length_score(text: str) -> float:
    """
    Word count sweet spot: 60-150 words  (≈ 30-60 s at ~2.5 words/sec).
    Too short = not enough content. Too long = loses focus.
    """
    word_count = len(text.split())
    if 60 <= word_count <= 150:
        return 10.0
    if word_count < 60:
        return max(0.0, word_count / 60 * 10.0)
    # > 150 words: gradual penalty
    return max(0.0, 10.0 - (word_count - 150) / 15)


def _density_score(text: str) -> float:
    """Short words (≤6 chars) ratio → direct, punchy language scores higher."""
    words = [w for w in text.split() if re.match(r"[a-zA-Z]", w)]
    if not words:
        return 0.0
    short = sum(1 for w in words if len(w) <= 6)
    return round(short / len(words) * 10.0, 2)


def _duration_score(duration_secs: float) -> float:
    """
    Ideal clip duration: 30-60 s for short-form content.
    Ramps up from 10 s, full score 30-60 s, penalty beyond 60 s.
    """
    if 30 <= duration_secs <= 60:
        return 10.0
    if duration_secs < 30:
        return max(0.0, (duration_secs - 10) / 20 * 10.0)
    # > 60 s: each extra 10 s loses ~3 points
    return max(0.0, 10.0 - (duration_secs - 60) / 10 * 3)


def _momentum_score(text: str) -> float:
    """
    Emotional density of the opening 30 words.
    Clips that hook immediately retain more viewers.
    """
    words = text.split()[:30]
    if not words:
        return 0.0
    opening = " ".join(words).lower()
    hits = sum(1 for w in re.findall(r"\b[a-z]+\b", opening) if w in EMOTION_WORDS)
    return min(hits / 3 * 10.0, 10.0)


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────


def compute_viral_score(text: str, duration_secs: float) -> float:
    """
    Compute a 0–10 viral potential score for a transcript segment.

    Parameters
    ----------
    text : str
        Transcript text of the segment.
    duration_secs : float
        Duration of the segment in seconds.

    Returns
    -------
    float – viral score between 0.0 and 10.0 (3 decimal places).
    """
    components = {
        "emotion": _emotion_score(text),
        "numbers": _numbers_score(text),
        "question": _question_score(text),
        "storytelling": _storytelling_score(text),
        "urgency": _urgency_score(text),
        "contrast": _contrast_score(text),
        "length": _length_score(text),
        "density": _density_score(text),
        "duration": _duration_score(duration_secs),
        "momentum": _momentum_score(text),
    }

    score = sum(WEIGHTS[k] * v for k, v in components.items())
    score = round(min(max(score, 0.0), 10.0), 3)

    logger.debug(
        f"Viral score: {score:.2f} | "
        + " | ".join(f"{k}={v:.1f}" for k, v in components.items())
    )
    return score
