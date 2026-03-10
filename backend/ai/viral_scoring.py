"""
viral_scoring.py – Compute a viral potential score for a text segment.

Score components (each 0–10, weighted sum normalised to 0–10):

  1. numbers_score      – presence of statistics / numbers
  2. emotion_score      – count of emotional trigger words
  3. question_score     – questions create curiosity
  4. length_score       – sweet spot: 20-60 words
  5. density_score      – short words ratio (direct, punchy language)
  6. duration_score     – clip duration in the ideal 15-45 s range

Weights are defined in WEIGHTS and can be tuned easily.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Emotional trigger words (extend freely)
# ──────────────────────────────────────────────
EMOTION_WORDS = {
    # Positive
    "amazing", "incredible", "unbelievable", "revolutionary", "breakthrough",
    "secret", "hidden", "revealed", "shocking", "insane", "mind-blowing",
    "powerful", "ultimate", "best", "perfect", "genius", "brilliant",
    "extraordinary", "phenomenal", "magnificent",
    # Negative / urgent
    "dangerous", "deadly", "terrifying", "scary", "forbidden",
    "illegal", "banned", "censored", "controversial", "dark",
    "tragic", "disaster", "crisis", "worst", "failed", "wrong",
    # Curiosity
    "why", "how", "what", "truth", "lie", "myth", "fact",
    "real", "fake", "never", "always", "everyone", "nobody",
    # Social proof
    "million", "billion", "viral", "trending", "popular", "famous",
}

# Component weights (must sum to 1.0)
WEIGHTS = {
    "numbers":  0.15,
    "emotion":  0.30,
    "question": 0.15,
    "length":   0.15,
    "density":  0.10,
    "duration": 0.10,
    "momentum": 0.05,   # bonus for high emotion density at the START of the clip
}


def _numbers_score(text: str) -> float:
    """Score based on presence of numbers, percentages, and statistics."""
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


def _emotion_score(text: str) -> float:
    """Score based on emotional trigger word density."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in EMOTION_WORDS)
    # Cap at 4 hits → 10.0
    return min(hits / 4 * 10.0, 10.0)


def _question_score(text: str) -> float:
    """Score based on number of questions."""
    count = text.count("?")
    return min(count * 5.0, 10.0)


def _length_score(text: str) -> float:
    """Score based on word count; sweet spot 20-60 words."""
    word_count = len(text.split())
    if 20 <= word_count <= 60:
        return 10.0
    if word_count < 20:
        return max(0.0, word_count / 20 * 10.0)
    # > 60 words: diminishing returns
    return max(0.0, 10.0 - (word_count - 60) / 10)


def _density_score(text: str) -> float:
    """
    Score based on information density.
    
    Short words (≤ 6 chars) tend to indicate direct, punchy language.
    Ratio of short words to total words → 0–10.
    """
    words = [w for w in text.split() if re.match(r"[a-zA-Z]", w)]
    if not words:
        return 0.0
    short = sum(1 for w in words if len(w) <= 6)
    return round(short / len(words) * 10.0, 2)


def _duration_score(duration_secs: float) -> float:
    """Score based on clip duration. Ideal: 15-45 s."""
    if 15 <= duration_secs <= 45:
        return 10.0
    if duration_secs < 15:
        return max(0.0, duration_secs / 15 * 10.0)
    # > 45 s: penalise linearly
    return max(0.0, 10.0 - (duration_secs - 45) / 5)


def _momentum_score(text: str) -> float:
    """
    Bonus for clips that open with a strong emotional hook.
    Checks the first 30 words for emotional trigger density.
    A clip that grabs attention immediately retains viewers better.
    """
    words = text.split()[:30]
    if not words:
        return 0.0
    opening = " ".join(words).lower()
    hits = sum(1 for w in re.findall(r"\b[a-z]+\b", opening) if w in EMOTION_WORDS)
    return min(hits / 3 * 10.0, 10.0)


def compute_viral_score(text: str, duration_secs: float) -> float:
    """
    Compute a 0–10 viral score for a transcript segment.

    Parameters
    ----------
    text : str
        Transcript text of the segment.
    duration_secs : float
        Duration of the segment in seconds.

    Returns
    -------
    float – viral score between 0 and 10.
    """
    components = {
        "numbers":  _numbers_score(text),
        "emotion":  _emotion_score(text),
        "question": _question_score(text),
        "length":   _length_score(text),
        "density":  _density_score(text),
        "duration": _duration_score(duration_secs),
        "momentum": _momentum_score(text),
    }

    score = sum(WEIGHTS[k] * v for k, v in components.items())
    score = round(min(max(score, 0.0), 10.0), 3)

    logger.debug(f"Viral score: {score:.2f} | components: {components}")
    return score
