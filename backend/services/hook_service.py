"""
hook_service.py – Generate viral hooks for each clip.

Fallback chain (most to least preferred):
  1. Ollama  – local LLM, zero cost, requires Ollama running
  2. Groq    – free cloud API (60 req/min on llama-3.3-70b), requires GROQ_API_KEY
  3. Rules   – deterministic heuristic, always available

Set GROQ_API_KEY in .env to enable the Groq fallback.
"""

import logging
import re
import requests

from backend.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Prompt template (shared by Ollama & Groq)
# ──────────────────────────────────────────────
HOOK_PROMPT = (
    "You are a viral social media expert. "
    "Rewrite the following sentence as a single viral hook for TikTok. "
    "Rules: max 12 words, start with a power word, create curiosity or urgency, "
    "do NOT use hashtags, output ONLY the hook sentence.\n\n"
    'Sentence: "{sentence}"\n\n'
    "Viral hook:"
)


# ──────────────────────────────────────────────
#  Level 1 – Ollama (local)
# ──────────────────────────────────────────────
def _call_ollama(prompt: str) -> str:
    """Call the local Ollama server. Raises on any error."""
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


# ──────────────────────────────────────────────
#  Level 2 – Groq (free cloud API)
# ──────────────────────────────────────────────
def _call_groq(prompt: str) -> str:
    """
    Call the Groq cloud API.

    Requires GROQ_API_KEY in .env.
    Free tier: 60 requests/min, 6 000 req/day on llama-3.3-70b-versatile.
    Raises ValueError if no API key is configured.
    Raises groq.APIError on network / auth issues.
    """
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not set — skipping Groq.")

    from groq import Groq  # lazy import

    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=60,
    )
    return (response.choices[0].message.content or "").strip()


# ──────────────────────────────────────────────
#  Level 3 – Rule-based (always works)
# ──────────────────────────────────────────────
def _rule_based_hook(text: str) -> str:
    """Deterministic fallback hook from the first sentence."""
    first = re.split(r"[.!?]", text)[0].strip()
    words = first.split()
    if len(words) > 12:
        first = " ".join(words[:12]) + "…"

    hooks = [
        f"You won't believe this: {first.lower()}",
        f"Nobody talks about this — {first.lower()}",
        f"Here's what changed everything: {first.lower()}",
    ]
    return hooks[hash(text) % len(hooks)]


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────
def generate_hook(segment_text: str) -> str:
    """
    Generate a viral hook for a transcript segment.

    Tries each level in order; moves to the next on any failure.

    Returns
    -------
    str – a short, punchy hook sentence (≤ 20 words).
    """
    excerpt = segment_text[:300].strip()
    if not excerpt:
        return "You need to see this."

    first_sentence = re.split(r"[.!?]", excerpt)[0].strip() or excerpt
    prompt = HOOK_PROMPT.format(sentence=first_sentence)

    def _is_valid(hook: str) -> bool:
        return bool(hook) and len(hook.split()) <= 20

    # ── Level 1: Ollama ──────────────────────────────────────────────────
    try:
        hook = _call_ollama(prompt)
        if _is_valid(hook):
            logger.debug(f"Hook via Ollama: {hook!r}")
            return hook
        logger.warning("Ollama hook too long or empty — trying Groq.")
    except Exception as exc:
        logger.info(f"Ollama unavailable ({type(exc).__name__}: {exc}) — trying Groq.")

    # ── Level 2: Groq ────────────────────────────────────────────────────
    try:
        hook = _call_groq(prompt)
        if _is_valid(hook):
            logger.debug(f"Hook via Groq: {hook!r}")
            return hook
        logger.warning("Groq hook too long or empty — using rule-based fallback.")
    except ValueError as exc:
        logger.info(str(exc))
    except Exception as exc:
        logger.warning(f"Groq failed ({type(exc).__name__}: {exc}) — using rule-based fallback.")

    # ── Level 3: Rule-based ──────────────────────────────────────────────
    hook = _rule_based_hook(segment_text)
    logger.debug(f"Hook via rules: {hook!r}")
    return hook
