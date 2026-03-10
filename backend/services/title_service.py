"""
title_service.py – Generate a catchy short title for a clip (Pro+ only).

Fallback chain:
  1. Groq  – llama-3.3-70b-versatile
  2. Rules – deterministic heuristic
"""

import logging
import re

from backend.config import settings

logger = logging.getLogger(__name__)

TITLE_PROMPT = (
    "You are a viral content strategist. "
    "Write a single catchy, short video title (max 8 words) for a short-form clip "
    "based on the following transcript excerpt. "
    "Rules: no hashtags, no quotes, no emojis, output ONLY the title.\n\n"
    'Transcript: "{text}"\n\n'
    "Title:"
)


def _call_groq(prompt: str) -> str:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not set.")
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=30,
    )
    return (response.choices[0].message.content or "").strip().strip('"').strip("'")


def _rule_based_title(text: str) -> str:
    first = re.split(r"[.!?]", text)[0].strip()
    words = first.split()
    if len(words) > 8:
        first = " ".join(words[:8])
    return first.capitalize()


def generate_title(segment_text: str) -> str:
    """Return a short catchy title (≤ 8 words) for the clip."""
    excerpt = segment_text[:400].strip()
    if not excerpt:
        return "Watch This"

    prompt = TITLE_PROMPT.format(text=excerpt[:300])

    try:
        title = _call_groq(prompt)
        if title and len(title.split()) <= 12:
            logger.debug(f"Title via Groq: {title!r}")
            return title
    except ValueError as exc:
        logger.info(str(exc))
    except Exception as exc:
        logger.warning(f"Groq title failed ({exc}) — using rule-based fallback.")

    title = _rule_based_title(excerpt)
    logger.debug(f"Title via rules: {title!r}")
    return title
