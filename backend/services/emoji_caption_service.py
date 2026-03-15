"""
emoji_caption_service.py – Build stylised emoji-enhanced captions for a clip.

Each caption line:
  - Is at most 6 words wide (for readability on mobile)
  - Has IMPORTANT words capitalised
  - Gets a contextual emoji appended when a keyword matches

Returns a list of caption line dicts:
    { "text": str, "start": float, "end": float }
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Emoji keyword dictionary
# ──────────────────────────────────────────────
EMOJI_MAP: Dict[str, str] = {
    # Tech / AI
    "ai": "🤖",
    "artificial intelligence": "🤖",
    "robot": "🤖",
    "code": "💻",
    "software": "💻",
    "program": "💻",
    "developer": "💻",
    "data": "📊",
    "algorithm": "⚙️",
    "machine learning": "🧠",
    # Money / Business
    "money": "💰",
    "million": "💰",
    "billion": "💰",
    "profit": "💰",
    "business": "💼",
    "startup": "🚀",
    "company": "🏢",
    "market": "📈",
    "stock": "📈",
    "invest": "💹",
    # Science / Space
    "science": "🔬",
    "research": "🔬",
    "study": "📚",
    "space": "🚀",
    "nasa": "🚀",
    "planet": "🪐",
    "universe": "🌌",
    # Health
    "health": "❤️",
    "brain": "🧠",
    "body": "💪",
    "exercise": "🏋️",
    "food": "🍎",
    "diet": "🥗",
    # Emotions / energy
    "amazing": "🤩",
    "incredible": "😱",
    "crazy": "🤪",
    "love": "❤️",
    "hate": "😤",
    "fear": "😨",
    "hope": "🌟",
    "win": "🏆",
    "success": "✅",
    "fail": "❌",
    "mistake": "⚠️",
    # Time
    "secret": "🤫",
    "truth": "💡",
    "fact": "📌",
    "future": "🔮",
    "history": "📜",
    "change": "🔄",
    # Nature
    "fire": "🔥",
    "water": "💧",
    "earth": "🌍",
    "energy": "⚡",
}

# Words that should always be uppercased for emphasis
EMPHASIS_WORDS = {
    "never",
    "always",
    "every",
    "all",
    "none",
    "nothing",
    "everything",
    "most",
    "best",
    "worst",
    "only",
    "must",
    "will",
    "can",
    "huge",
    "massive",
    "insane",
    "secret",
    "real",
    "true",
    "free",
    "now",
    "today",
    "first",
    "last",
    "new",
    "big",
    "zero",
    "one",
}

MAX_WORDS_PER_LINE = 6


def _find_emoji(text: str) -> str:
    """Return the first matching emoji for keywords found in text."""
    text_lower = text.lower()
    for keyword, emoji in EMOJI_MAP.items():
        if keyword in text_lower:
            return emoji
    return ""


def _stylise_word(word: str) -> str:
    """Uppercase a word if it belongs to the emphasis list."""
    clean = re.sub(r"[^a-zA-Z]", "", word).lower()
    return word.upper() if clean in EMPHASIS_WORDS else word


def _split_into_lines(text: str, max_words: int = MAX_WORDS_PER_LINE) -> List[str]:
    """Split a sentence into lines of at most max_words words."""
    words = text.split()
    lines = []
    for i in range(0, len(words), max_words):
        chunk = words[i : i + max_words]
        lines.append(" ".join(chunk))
    return lines


def build_captions(
    segment_text: str,
    word_timestamps: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Build styled caption lines from a transcript segment.

    Parameters
    ----------
    segment_text : str
        Raw transcript text of the segment.
    word_timestamps : list, optional
        Word-level timestamps from Whisper (absolute times).
        When provided, each caption line gets accurate start/end times.
        Falls back to evenly distributed timing.

    Returns
    -------
    list of { "text": str, "start": float, "end": float }
    """
    # ── 1. Stylise words ──────────────────────────────────────────────────
    words_in_text = segment_text.split()
    styled_words = [_stylise_word(w) for w in words_in_text]
    styled_text = " ".join(styled_words)

    # ── 2. Split into short lines ────────────────────────────────────────
    lines = _split_into_lines(styled_text)

    # ── 3. Add emojis ─────────────────────────────────────────────────────
    result_lines = []
    for line in lines:
        emoji = _find_emoji(line)
        display = f"{line} {emoji}".strip() if emoji else line
        result_lines.append(display)

    # ── 4. Assign timestamps ─────────────────────────────────────────────
    captions: List[Dict[str, Any]] = []

    if word_timestamps:
        # Use word timestamps sequentially — avoids duplicate-word lookup errors.
        # Each line gets the time range of its corresponding words in order.
        wt_list = [w for w in word_timestamps if "start" in w and "end" in w]
        word_idx = 0  # pointer into wt_list

        for line in result_lines:
            # Count how many original words this line contains (strip emojis for counting)
            line_word_count = len(re.sub(r"[^\w\s]", "", line).split())
            line_word_count = max(1, line_word_count)

            # Grab the timestamp slice for those words
            slice_end = min(word_idx + line_word_count, len(wt_list))
            ts_slice = wt_list[word_idx:slice_end]

            if ts_slice:
                t_start = ts_slice[0]["start"]
                t_end = ts_slice[-1]["end"]
                captions.append({"text": line, "start": t_start, "end": t_end})
                word_idx = slice_end
            else:
                # Ran out of timestamps — extend from last known end
                prev_end = captions[-1]["end"] if captions else 0.0
                captions.append(
                    {"text": line, "start": prev_end, "end": prev_end + 1.5}
                )
    else:
        # No timestamps: evenly distribute over segment
        avg_line_dur = 1.5  # seconds per line
        t = 0.0
        for line in result_lines:
            captions.append({"text": line, "start": t, "end": t + avg_line_dur})
            t += avg_line_dur

    logger.debug(f"Built {len(captions)} caption lines.")
    return captions
