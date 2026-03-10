"""
hashtag_service.py – Generate relevant hashtags for a clip (Pro+ only).

Fallback chain:
  1. Groq  – llama-3.3-70b-versatile
  2. Rules – keyword extraction heuristic
"""

import logging
import re

from backend.config import settings

logger = logging.getLogger(__name__)

HASHTAG_PROMPT = (
    "You are a viral social media expert. "
    "Generate exactly 5 relevant hashtags for a short-form video clip based on "
    "the following transcript excerpt. "
    "Rules: start each with #, lowercase, no spaces inside, relevant to the content, "
    "output ONLY the 5 hashtags separated by spaces.\n\n"
    'Transcript: "{text}"\n\n'
    "Hashtags:"
)


def _call_groq(prompt: str) -> list[str]:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not set.")
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=60,
    )
    raw = (response.choices[0].message.content or "").strip()
    # Extract all tokens starting with #
    tags = re.findall(r"#\w+", raw)
    return tags[:7]  # keep at most 7


def _rule_based_hashtags(text: str) -> list[str]:
    """Extract the most common meaningful words as hashtags."""
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "it", "this", "that", "was", "are", "be", "have",
        "i", "you", "we", "he", "she", "they", "do", "not", "so", "if", "as",
    }
    words = re.findall(r"\b[a-z]{4,}\b", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    top = sorted(freq, key=lambda w: freq[w], reverse=True)[:5]
    return [f"#{w}" for w in top] or ["#shorts", "#viral", "#trending", "#fyp", "#reels"]


def generate_hashtags(segment_text: str) -> list[str]:
    """Return a list of 5 hashtags for the clip."""
    excerpt = segment_text[:400].strip()
    if not excerpt:
        return ["#shorts", "#viral", "#trending", "#fyp", "#reels"]

    prompt = HASHTAG_PROMPT.format(text=excerpt[:300])

    try:
        tags = _call_groq(prompt)
        if len(tags) >= 3:
            logger.debug(f"Hashtags via Groq: {tags}")
            return tags
    except ValueError as exc:
        logger.info(str(exc))
    except Exception as exc:
        logger.warning(f"Groq hashtags failed ({exc}) — using rule-based fallback.")

    tags = _rule_based_hashtags(excerpt)
    logger.debug(f"Hashtags via rules: {tags}")
    return tags
