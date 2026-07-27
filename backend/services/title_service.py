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

# Supported title languages and their localized instructions.
TITLE_PROMPTS = {
    "en": (
        "You are a viral content strategist. "
        "Write a single catchy, short video title (max 8 words) for a short-form clip "
        "based on the following transcript excerpt. "
        "Rules: no hashtags, no quotes, no emojis, output ONLY the title.\n\n"
        'Transcript: "{text}"\n\n'
        "Title:"
    ),
    "fr": (
        "Tu es un stratège de contenu viral. "
        "Écris un titre court et accrocheur pour un clip vidéo (max 8 mots) "
        "basé sur l'extrait de transcription suivant. "
        "Règles: pas de hashtags, pas de guillemets, pas d'émojis, écris SEULEMENT le titre en français.\n\n"
        'Transcription: "{text}"\n\n'
        "Titre:"
    ),
    "es": (
        "Eres un estratega de contenido viral. "
        "Escribe un título corto y atractivo para un clip de video (máx 8 palabras) "
        "basado en el siguiente fragmento de transcripción. "
        "Reglas: sin hashtags, sin comillas, sin emojis, escribe SOLO el título en español.\n\n"
        'Transcripción: "{text}"\n\n'
        "Título:"
    ),
    "de": (
        "Du bist ein Stratege für virale Inhalte. "
        "Schreibe einen kurzen und prägnanten Videotitel (max 8 Wörter) für einen Short-Form-Clip "
        "basierend auf dem folgenden Transkriptauszug. "
        "Regeln: keine Hashtags, keine Anführungszeichen, keine Emojis, schreibe NUR den Titel auf Deutsch.\n\n"
        'Transkript: "{text}"\n\n'
        "Titel:"
    ),
}

DEFAULT_PROMPT = TITLE_PROMPTS["en"]
SUPPORTED_TITLE_LANGUAGES = frozenset(TITLE_PROMPTS)
_TITLE_PREFIX_RE = re.compile(r"^(?:title|titre|t[íi]tulo|titel)\s*(?::|-)\s*", re.IGNORECASE)


def normalize_supported_language(value: object) -> str | None:
    """Normalize a supported title language, or return None when unsupported."""
    if not isinstance(value, str):
        return None

    normalized = value.strip().replace("_", "-").lower()
    if not normalized or normalized == "auto":
        return None

    primary_code = normalized.split("-", 1)[0]
    return primary_code if primary_code in SUPPORTED_TITLE_LANGUAGES else None


def normalize_title_language(value: object) -> str:
    """Return a supported ISO-639-1 language code, defaulting to English."""
    return normalize_supported_language(value) or "en"


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
    return first.capitalize() or "Watch This"


def _clean_title(title: str) -> str:
    """Normalize common provider formatting without changing title semantics."""
    first_line = next((line.strip() for line in title.splitlines() if line.strip()), "")
    first_line = _TITLE_PREFIX_RE.sub("", first_line).strip()
    return first_line.strip().strip('"').strip("'").strip("«").strip("»").strip()


def generate_title(segment_text: str, language: str | None = None) -> str:
    """Return a short catchy title (≤ 8 words) for the clip in the specified language."""
    excerpt = segment_text[:400].strip()
    if not excerpt:
        return "Watch This"

    lang_code = normalize_title_language(language)
    prompt_template = TITLE_PROMPTS.get(lang_code, DEFAULT_PROMPT)
    prompt = prompt_template.format(text=excerpt[:300])

    try:
        title = _clean_title(_call_groq(prompt))
        if title and len(title.split()) <= 12:
            logger.debug("Generated title via Groq (language=%s)", lang_code)
            return title
    except ValueError as exc:
        logger.info(str(exc))
    except Exception:
        logger.warning("Groq title generation failed; using rule-based fallback.")

    title = _rule_based_title(excerpt)
    logger.debug("Generated title via rules (language=%s)", lang_code)
    return title
