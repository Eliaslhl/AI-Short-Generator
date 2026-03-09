"""
hook_service.py – Generate viral hooks for each clip using Ollama (local LLM).

Falls back to a simple rule-based hook if Ollama is not running.
"""

import logging
import re
import requests

from backend.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Prompt template
# ──────────────────────────────────────────────
HOOK_PROMPT = (
    "You are a viral social media expert. "
    "Rewrite the following sentence as a single viral hook for TikTok. "
    "Rules: max 12 words, start with a power word, create curiosity or urgency, "
    "do NOT use hashtags, output ONLY the hook sentence.\n\n"
    'Sentence: "{sentence}"\n\n'
    "Viral hook:"
)


def _call_ollama(prompt: str) -> str:
    """
    Send a prompt to the local Ollama server and return the response text.

    Raises requests.exceptions.ConnectionError if Ollama is not running.
    """
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model":  settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "num_predict": 60,
        },
    }
    resp = requests.post(url, json=payload, timeout=settings.ollama_timeout)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _rule_based_hook(text: str) -> str:
    """
    Fallback: build a hook from the first sentence using simple heuristics.
    """
    # Take first sentence
    first = re.split(r"[.!?]", text)[0].strip()
    words = first.split()

    # Trim to 12 words and add a curiosity suffix
    if len(words) > 12:
        first = " ".join(words[:12]) + "…"

    # Make it feel urgent / intriguing
    hooks = [
        f"You won't believe this: {first.lower()}",
        f"Nobody talks about this — {first.lower()}",
        f"Here's what changed everything: {first.lower()}",
    ]
    # Pick deterministically based on text hash
    return hooks[hash(text) % len(hooks)]


def generate_hook(segment_text: str) -> str:
    """
    Generate a viral hook for a transcript segment.

    Tries Ollama first; falls back to the rule-based generator if unavailable.

    Parameters
    ----------
    segment_text : str
        The full transcript text of the segment.

    Returns
    -------
    str – a short, punchy hook sentence.
    """
    # Use only the first 300 characters to keep the prompt short
    excerpt = segment_text[:300].strip()
    if not excerpt:
        return "You need to see this."

    # Extract first sentence for the prompt
    first_sentence = re.split(r"[.!?]", excerpt)[0].strip()
    if not first_sentence:
        first_sentence = excerpt

    prompt = HOOK_PROMPT.format(sentence=first_sentence)

    try:
        hook = _call_ollama(prompt)
        # Sanity-check: must be non-empty and reasonably short
        if hook and len(hook.split()) <= 20:
            logger.debug(f"Ollama hook: {hook}")
            return hook
        logger.warning("Ollama returned a hook that seems too long; using fallback.")
    except Exception as exc:
        logger.warning(f"Ollama unavailable ({exc}); using rule-based hook fallback.")

    return _rule_based_hook(segment_text)
